"""MCP server for the Horos AI backend.

Dual transport: stdio (for local Claude Code) and SSE (for remote/Docker).
Provides tools for querying studies, triggering pipelines, and accessing
Horos domain knowledge.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from src.mcp import knowledge, tools

logger = logging.getLogger(__name__)

server = Server("neuro-dicom-ai")

# ── Tool definitions ──

TOOL_DEFS = [
    Tool(
        name="horos_query_study",
        description="Query PACS for studies by patient name/ID, date, or modality",
        inputSchema={
            "type": "object",
            "properties": {
                "patient_name": {"type": "string", "description": "Patient name (DICOM PN format, wildcards OK)"},
                "patient_id": {"type": "string", "description": "Patient ID"},
                "study_date": {"type": "string", "description": "Study date (YYYYMMDD or range YYYYMMDD-YYYYMMDD)"},
                "modality": {"type": "string", "description": "Modality filter (CT, MR, etc.)"},
            },
        },
    ),
    Tool(
        name="horos_get_series",
        description="List all series in a study, including AI-generated overlays",
        inputSchema={
            "type": "object",
            "properties": {
                "study_id": {"type": "string", "description": "Orthanc study ID"},
            },
            "required": ["study_id"],
        },
    ),
    Tool(
        name="horos_trigger_segmentation",
        description="Manually trigger AI segmentation pipeline for a study",
        inputSchema={
            "type": "object",
            "properties": {
                "study_id": {"type": "string", "description": "Orthanc study ID"},
                "pipeline": {"type": "string", "enum": ["cta", "mri"], "description": "Pipeline to run"},
            },
            "required": ["study_id"],
        },
    ),
    Tool(
        name="horos_pipeline_status",
        description="Check the status of a running or completed segmentation job",
        inputSchema={
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID returned by trigger"},
            },
            "required": ["job_id"],
        },
    ),
    Tool(
        name="horos_list_models",
        description="List available AI segmentation models and their configurations",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="horos_get_config",
        description="Read current AE titles, routing rules, model settings, and pipeline configuration",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="horos_architecture_guide",
        description="Get architecture documentation for a subsystem (overview, horos-capabilities, dicom-flow, pipeline/cta, pipeline/mri)",
        inputSchema={
            "type": "object",
            "properties": {
                "subsystem": {
                    "type": "string",
                    "description": "Subsystem name: architecture, horos-capabilities, dicom-flow, pipeline/cta, pipeline/mri",
                },
            },
        },
    ),
    Tool(
        name="horos_logs",
        description="Tail recent logs from AI service or Orthanc",
        inputSchema={
            "type": "object",
            "properties": {
                "service": {"type": "string", "enum": ["ai", "orthanc"], "default": "ai"},
                "lines": {"type": "integer", "default": 50},
            },
        },
    ),
    Tool(
        name="horos_llm_generate",
        description="Generate text using the on-device LLM (Ollama) — for reports, triage, explanations",
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Prompt for the LLM"},
                "system": {"type": "string", "description": "Optional system prompt"},
                "model": {"type": "string", "description": "Ollama model name (default: llama3.2:3b)"},
            },
            "required": ["prompt"],
        },
    ),
    Tool(
        name="horos_llm_models",
        description="List LLM models available in Ollama on the AI server",
        inputSchema={"type": "object", "properties": {}},
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOL_DEFS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool calls to implementation functions."""
    handler_map = {
        "horos_query_study": tools.horos_query_study,
        "horos_get_series": tools.horos_get_series,
        "horos_trigger_segmentation": tools.horos_trigger_segmentation,
        "horos_pipeline_status": tools.horos_pipeline_status,
        "horos_list_models": tools.horos_list_models,
        "horos_get_config": tools.horos_get_config,
        "horos_architecture_guide": tools.horos_architecture_guide,
        "horos_logs": tools.horos_logs,
        "horos_llm_generate": tools.horos_llm_generate,
        "horos_llm_models": tools.horos_llm_models,
    }

    handler = handler_map.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(**arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ── Resource definitions ──

@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(uri=uri, name=title, mimeType="text/markdown")
        for uri, (title, _) in knowledge.RESOURCES.items()
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    uri_str = str(uri)
    if uri_str in knowledge.RESOURCES:
        _, content = knowledge.RESOURCES[uri_str]
        return content
    raise ValueError(f"Unknown resource: {uri_str}")


# ── Entrypoints ──

async def run_stdio() -> None:
    """Run MCP server over stdio (for Claude Code local integration)."""
    _configure_from_env()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_sse(host: str = "0.0.0.0", port: int = 3001) -> None:
    """Run MCP server over SSE (for remote/Docker access)."""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    import uvicorn

    _configure_from_env()
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    config = uvicorn.Config(starlette_app, host=host, port=port)
    srv = uvicorn.Server(config)
    await srv.serve()


def _configure_from_env() -> None:
    """Configure tool URLs from environment variables."""
    orthanc_url = os.getenv("ORTHANC_URL", "http://localhost:8042")
    ai_service_url = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
    tools.configure(orthanc_url, ai_service_url)


def main() -> None:
    """CLI entrypoint for the MCP server."""
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Neuro DICOM AI MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="SSE host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3001, help="SSE port (default: 3001)")
    args = parser.parse_args()

    if args.transport == "sse":
        asyncio.run(run_sse(args.host, args.port))
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
