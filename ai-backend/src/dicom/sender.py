"""C-STORE sender for returning results to PACS (M1 implementation)."""

from __future__ import annotations


async def store_to_pacs(dicom_bytes: bytes | list[bytes], destination_ae: str = "PACS_CORE") -> None:
    """Send DICOM objects back to PACS via Orthanc's REST API.

    Uses Orthanc's /modalities/{name}/store endpoint for C-STORE.
    To be implemented in M1.
    """
    raise NotImplementedError("C-STORE sender not yet implemented")
