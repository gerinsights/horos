"""Tests for DICOM output generation (RTSTRUCT, Secondary Capture, SEG)."""

from __future__ import annotations

import numpy as np
import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid

from src.dicom.output import create_rtstruct, create_secondary_captures
from src.pipeline.base import SegmentationResult


def _make_source_datasets(num_slices: int = 10, rows: int = 64, cols: int = 64):
    """Create mock source DICOM datasets for testing."""
    series_uid = generate_uid()
    study_uid = generate_uid()
    frame_uid = generate_uid()

    datasets = []
    for i in range(num_slices):
        ds = Dataset()
        ds.file_meta = pydicom.dataset.FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT
        ds.SOPInstanceUID = generate_uid()
        ds.StudyInstanceUID = study_uid
        ds.SeriesInstanceUID = series_uid
        ds.FrameOfReferenceUID = frame_uid

        ds.PatientName = "Test^Patient"
        ds.PatientID = "TEST001"
        ds.StudyDate = "20260310"
        ds.StudyTime = "120000"
        ds.StudyDescription = "CTA Head"
        ds.StudyID = "1"
        ds.AccessionNumber = "A001"
        ds.Modality = "CT"

        ds.Rows = rows
        ds.Columns = cols
        ds.ImagePositionPatient = [0.0, 0.0, float(i * 2.0)]
        ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        ds.PixelSpacing = [0.5, 0.5]
        ds.SliceThickness = 2.0
        ds.SliceLocation = float(i * 2.0)

        ds.BitsAllocated = 16
        ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.RescaleIntercept = -1024
        ds.RescaleSlope = 1
        ds.WindowCenter = 400
        ds.WindowWidth = 1000

        pixels = (np.random.randn(rows, cols) * 200 + 400).astype(np.int16)
        ds.PixelData = pixels.tobytes()

        datasets.append(ds)

    return datasets


def _make_segmentation_result(
    num_slices: int = 10, rows: int = 64, cols: int = 64,
) -> SegmentationResult:
    """Create a test segmentation result with a sphere-like mask."""
    mask = np.zeros((num_slices, rows, cols), dtype=np.uint8)
    for z in range(3, 7):
        for y in range(25, 40):
            for x in range(25, 40):
                if (z - 5) ** 2 + (y - 32) ** 2 + (x - 32) ** 2 < 100:
                    mask[z, y, x] = 1

    return SegmentationResult(
        mask=mask,
        labels={1: "Right carotid", 2: "Left carotid"},
        spacing=(2.0, 0.5, 0.5),
        origin=(0.0, 0.0, 0.0),
    )


# --- SegmentationResult dataclass ---

def test_segmentation_result_defaults():
    mask = np.zeros((10, 10, 10), dtype=np.int32)
    result = SegmentationResult(mask=mask)
    assert result.spacing == (1.0, 1.0, 1.0)
    assert result.labels == {}


def test_segmentation_result_with_labels():
    mask = np.zeros((5, 5, 5), dtype=np.int32)
    mask[2, 2, 2] = 1
    result = SegmentationResult(
        mask=mask,
        labels={1: "Intracranial arteries"},
        spacing=(0.7, 0.7, 0.7),
    )
    assert result.labels[1] == "Intracranial arteries"
    assert result.spacing == (0.7, 0.7, 0.7)


# --- RTSTRUCT ---

def test_create_rtstruct_basic():
    source_ds = _make_source_datasets()
    result = _make_segmentation_result()
    rtstruct = create_rtstruct(result, source_ds)

    assert rtstruct.Modality == "RTSTRUCT"
    assert rtstruct.SOPClassUID == "1.2.840.10008.5.1.4.1.1.481.3"
    assert rtstruct.PatientID == "TEST001"
    assert rtstruct.StudyInstanceUID == source_ds[0].StudyInstanceUID


def test_create_rtstruct_has_contours():
    source_ds = _make_source_datasets()
    result = _make_segmentation_result()
    rtstruct = create_rtstruct(result, source_ds)

    assert len(rtstruct.StructureSetROISequence) > 0
    assert len(rtstruct.ROIContourSequence) > 0

    roi_contour = rtstruct.ROIContourSequence[0]
    assert hasattr(roi_contour, "ContourSequence")
    assert len(roi_contour.ContourSequence) > 0


def test_create_rtstruct_roi_names():
    source_ds = _make_source_datasets()
    result = _make_segmentation_result()
    rtstruct = create_rtstruct(result, source_ds)

    roi_names = [roi.ROIName for roi in rtstruct.StructureSetROISequence]
    assert "Right carotid" in roi_names


def test_create_rtstruct_contour_geometry():
    source_ds = _make_source_datasets()
    result = _make_segmentation_result()
    rtstruct = create_rtstruct(result, source_ds)

    contour = rtstruct.ROIContourSequence[0].ContourSequence[0]
    assert contour.ContourGeometricType == "CLOSED_PLANAR"
    assert contour.NumberOfContourPoints > 2
    assert len(contour.ContourData) == contour.NumberOfContourPoints * 3


# --- Secondary Capture ---

def test_create_secondary_captures():
    source_ds = _make_source_datasets()
    result = _make_segmentation_result()
    captures = create_secondary_captures(result, source_ds)

    assert len(captures) > 0
    sc = captures[0]
    assert sc.SOPClassUID == "1.2.840.10008.5.1.4.1.1.7"
    assert sc.SamplesPerPixel == 3
    assert sc.PhotometricInterpretation == "RGB"
    assert sc.BitsAllocated == 8
    assert sc.PatientID == "TEST001"


def test_secondary_capture_has_rgb_pixels():
    source_ds = _make_source_datasets()
    result = _make_segmentation_result()
    captures = create_secondary_captures(result, source_ds)

    sc = captures[0]
    pixel_data = np.frombuffer(sc.PixelData, dtype=np.uint8)
    assert len(pixel_data) == sc.Rows * sc.Columns * 3


def test_secondary_captures_share_series_uid():
    source_ds = _make_source_datasets()
    result = _make_segmentation_result()
    captures = create_secondary_captures(result, source_ds)

    if len(captures) > 1:
        assert captures[0].SeriesInstanceUID == captures[1].SeriesInstanceUID


def test_empty_mask_produces_no_captures():
    source_ds = _make_source_datasets()
    result = SegmentationResult(
        mask=np.zeros((10, 64, 64), dtype=np.uint8),
        labels={1: "Empty"},
    )
    captures = create_secondary_captures(result, source_ds)
    assert len(captures) == 0
