#!/usr/bin/env bash
# Download model weights into the models/ directory (Docker volume mount).
# Usage: ./scripts/download_models.sh [model_name]
# Available models: cta_vessels, brain_extraction, tissue_segmentation
#
# Weights are downloaded from HuggingFace Hub or Zenodo.
# This script is idempotent — existing weights are skipped.

set -euo pipefail

MODELS_DIR="${MODELS_DIR:-$(dirname "$0")/../models}"
mkdir -p "$MODELS_DIR"

download_if_missing() {
    local name="$1"
    local url="$2"
    local dest="$3"

    if [ -e "$dest" ]; then
        echo "[skip] $name already exists at $dest"
        return
    fi

    echo "[download] $name → $dest"
    mkdir -p "$(dirname "$dest")"
    curl -fSL --progress-bar "$url" -o "$dest"
    echo "[done] $name"
}

# ── Model definitions ──
# Update URLs when actual model weights are available.

download_cta_vessels() {
    echo "=== CTA Vessel Segmentation (nnUNet v2) ==="
    local dir="$MODELS_DIR/nnunet/cta_vessels"
    mkdir -p "$dir"

    # Placeholder — replace with actual model URLs
    echo "NOTE: CTA vessel model weights not yet available."
    echo "Expected structure:"
    echo "  $dir/plans.json"
    echo "  $dir/fold_0/checkpoint_final.pth"
    echo "  $dir/fold_1/checkpoint_final.pth"
    echo "  $dir/dataset.json"
}

download_brain_extraction() {
    echo "=== Brain Extraction (MONAI) ==="
    local dir="$MODELS_DIR/monai/brain_extraction"
    mkdir -p "$dir"

    echo "NOTE: Brain extraction model weights not yet available."
    echo "Expected structure:"
    echo "  $dir/model.pt"
    echo "  $dir/config.json"
}

download_tissue_segmentation() {
    echo "=== Tissue Segmentation (nnUNet v2) ==="
    local dir="$MODELS_DIR/nnunet/tissue_seg"
    mkdir -p "$dir"

    echo "NOTE: Tissue segmentation model weights not yet available."
    echo "Expected structure:"
    echo "  $dir/plans.json"
    echo "  $dir/fold_0/checkpoint_final.pth"
    echo "  $dir/dataset.json"
}

# ── Main ──

MODEL="${1:-all}"

case "$MODEL" in
    cta_vessels)         download_cta_vessels ;;
    brain_extraction)    download_brain_extraction ;;
    tissue_segmentation) download_tissue_segmentation ;;
    all)
        download_cta_vessels
        echo ""
        download_brain_extraction
        echo ""
        download_tissue_segmentation
        ;;
    *)
        echo "Unknown model: $MODEL"
        echo "Available: cta_vessels, brain_extraction, tissue_segmentation, all"
        exit 1
        ;;
esac

echo ""
echo "Models directory: $MODELS_DIR"
ls -la "$MODELS_DIR"
