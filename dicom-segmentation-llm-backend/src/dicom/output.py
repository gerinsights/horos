"""DICOM output generation: RTSTRUCT + Secondary Capture + SEG.

Triple output strategy:
- RTSTRUCT: Interactive contour overlays (supported by most PACS viewers)
- Secondary Capture: Burned-in color overlay (universal viewer support)
- SEG: Voxel-level archive (OHIF, 3D Slicer interop)
"""

from __future__ import annotations

import datetime
import logging
from typing import Sequence

import numpy as np
import pydicom
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence as DicomSequence
from pydicom.uid import generate_uid

from src.pipeline.base import SegmentationResult

logger = logging.getLogger(__name__)

# Colors for segmentation labels (RGB, 0-255)
LABEL_COLORS = {
    1: (255, 0, 0),      # Red
    2: (0, 0, 255),      # Blue
    3: (255, 165, 0),    # Orange
    4: (0, 255, 255),    # Cyan
    5: (0, 255, 0),      # Green
    6: (255, 255, 0),    # Yellow
    7: (255, 0, 255),    # Magenta
    8: (128, 0, 128),    # Purple
}


def create_rtstruct(
    result: SegmentationResult,
    source_datasets: list[Dataset],
) -> Dataset:
    """Create a DICOM RTSTRUCT from a segmentation result.

    Finds contours on each slice of the label map and encodes them as
    CLOSED_PLANAR contours in DICOM patient coordinate space.

    Args:
        result: SegmentationResult with mask (D, H, W) and labels dict.
        source_datasets: pydicom Datasets of the original DICOM images (one per slice).

    Returns:
        pydicom Dataset ready for writing/sending.
    """
    from skimage import measure as sk_measure

    ds = Dataset()
    ds.file_meta = pydicom.dataset.FileMetaDataset()
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.3"
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.481.3"
    ds.SOPInstanceUID = ds.file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "RTSTRUCT"
    ds.Manufacturer = "DICOM Segmentation Backend"
    ds.SeriesDescription = "AI Segmentation"
    ds.StructureSetLabel = "AI_SEG"
    ds.StructureSetDate = datetime.date.today().strftime("%Y%m%d")
    ds.StructureSetTime = datetime.datetime.now().strftime("%H%M%S")

    # Copy patient/study info from source
    ref = source_datasets[0]
    for attr in ("PatientName", "PatientID", "PatientBirthDate", "PatientSex",
                 "StudyInstanceUID", "StudyDate", "StudyTime", "StudyDescription",
                 "StudyID", "AccessionNumber"):
        if hasattr(ref, attr):
            setattr(ds, attr, getattr(ref, attr))

    ds.SeriesInstanceUID = generate_uid()
    ds.SeriesNumber = 999

    # ReferencedFrameOfReferenceSequence
    frame_of_ref_uid = getattr(ref, "FrameOfReferenceUID", generate_uid())
    ref_frame_seq_item = Dataset()
    ref_frame_seq_item.FrameOfReferenceUID = frame_of_ref_uid

    ref_study_item = Dataset()
    ref_study_item.ReferencedSOPClassUID = "1.2.840.10008.3.1.2.3.1"
    ref_study_item.ReferencedSOPInstanceUID = ref.StudyInstanceUID

    ref_series_item = Dataset()
    ref_series_item.SeriesInstanceUID = ref.SeriesInstanceUID

    contour_images = DicomSequence()
    for src_ds in source_datasets:
        img_item = Dataset()
        img_item.ReferencedSOPClassUID = src_ds.SOPClassUID
        img_item.ReferencedSOPInstanceUID = src_ds.SOPInstanceUID
        contour_images.append(img_item)

    ref_series_item.ContourImageSequence = contour_images
    ref_study_item.RTReferencedSeriesSequence = DicomSequence([ref_series_item])
    ref_frame_seq_item.RTReferencedStudySequence = DicomSequence([ref_study_item])
    ds.ReferencedFrameOfReferenceSequence = DicomSequence([ref_frame_seq_item])

    # Build StructureSetROISequence and ROIContourSequence
    roi_seq = DicomSequence()
    contour_seq = DicomSequence()

    for label_id, label_name in result.labels.items():
        if label_id == 0:
            continue

        roi_item = Dataset()
        roi_item.ROINumber = label_id
        roi_item.ReferencedFrameOfReferenceUID = frame_of_ref_uid
        roi_item.ROIName = label_name
        roi_item.ROIGenerationAlgorithm = "AUTOMATIC"
        roi_seq.append(roi_item)

        color = LABEL_COLORS.get(label_id, (255, 255, 255))
        contour_item = Dataset()
        contour_item.ROIDisplayColor = list(color)
        contour_item.ReferencedROINumber = label_id

        slice_contours = DicomSequence()

        for slice_idx in range(result.mask.shape[0]):
            slice_mask = (result.mask[slice_idx] == label_id).astype(np.uint8)
            if slice_mask.sum() == 0:
                continue

            if slice_idx >= len(source_datasets):
                continue

            src_ds = source_datasets[slice_idx]
            ipp = [float(x) for x in src_ds.ImagePositionPatient]
            iop = [float(x) for x in src_ds.ImageOrientationPatient]
            ps = [float(x) for x in src_ds.PixelSpacing]

            contours = sk_measure.find_contours(slice_mask, 0.5)

            for contour_points in contours:
                if len(contour_points) < 3:
                    continue

                dicom_points = []
                for row, col in contour_points:
                    x = ipp[0] + col * ps[1] * iop[0] + row * ps[0] * iop[3]
                    y = ipp[1] + col * ps[1] * iop[1] + row * ps[0] * iop[4]
                    z = ipp[2] + col * ps[1] * iop[2] + row * ps[0] * iop[5]
                    dicom_points.extend([x, y, z])

                c_item = Dataset()
                c_item.ContourGeometricType = "CLOSED_PLANAR"
                c_item.NumberOfContourPoints = len(contour_points)
                c_item.ContourData = [f"{v:.6f}" for v in dicom_points]

                c_img_item = Dataset()
                c_img_item.ReferencedSOPClassUID = src_ds.SOPClassUID
                c_img_item.ReferencedSOPInstanceUID = src_ds.SOPInstanceUID
                c_item.ContourImageSequence = DicomSequence([c_img_item])

                slice_contours.append(c_item)

        contour_item.ContourSequence = slice_contours
        contour_seq.append(contour_item)

    ds.StructureSetROISequence = roi_seq
    ds.ROIContourSequence = contour_seq

    # RTROIObservationsSequence (required)
    obs_seq = DicomSequence()
    for label_id, label_name in result.labels.items():
        if label_id == 0:
            continue
        obs = Dataset()
        obs.ObservationNumber = label_id
        obs.ReferencedROINumber = label_id
        obs.RTROIInterpretedType = "ORGAN"
        obs.ROIInterpreter = ""
        obs_seq.append(obs)
    ds.RTROIObservationsSequence = obs_seq

    logger.info("Created RTSTRUCT with %d ROIs", len(roi_seq))
    return ds


def create_secondary_captures(
    result: SegmentationResult,
    source_datasets: list[Dataset],
    opacity: float = 0.4,
) -> list[Dataset]:
    """Create Secondary Capture DICOM series with color overlay burned in.

    Args:
        result: SegmentationResult with mask and labels.
        source_datasets: Original DICOM datasets (with pixel data).
        opacity: Overlay opacity (0.0 = transparent, 1.0 = opaque).

    Returns:
        List of pydicom Datasets (one per slice that has segmentation).
    """
    sc_series_uid = generate_uid()
    captures = []

    for slice_idx in range(min(result.mask.shape[0], len(source_datasets))):
        slice_mask = result.mask[slice_idx]
        if slice_mask.max() == 0:
            continue

        src_ds = source_datasets[slice_idx]

        try:
            pixels = src_ds.pixel_array.astype(np.float32)
        except Exception:
            continue

        # Apply window/level
        wc = float(getattr(src_ds, "WindowCenter", [400])[0]) if hasattr(src_ds, "WindowCenter") else 400
        ww = float(getattr(src_ds, "WindowWidth", [1000])[0]) if hasattr(src_ds, "WindowWidth") else 1000

        if isinstance(wc, pydicom.multival.MultiValue):
            wc = float(wc[0])
        if isinstance(ww, pydicom.multival.MultiValue):
            ww = float(ww[0])

        low = wc - ww / 2
        high = wc + ww / 2
        gray = np.clip((pixels - low) / (high - low) * 255, 0, 255).astype(np.uint8)

        rgb = np.stack([gray, gray, gray], axis=-1)

        for label_id in np.unique(slice_mask):
            if label_id == 0:
                continue
            color = LABEL_COLORS.get(int(label_id), (255, 255, 255))
            region = slice_mask == label_id
            for c in range(3):
                rgb[region, c] = (
                    (1 - opacity) * rgb[region, c] + opacity * color[c]
                ).astype(np.uint8)

        sc = Dataset()
        sc.file_meta = pydicom.dataset.FileMetaDataset()
        sc.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
        sc.file_meta.MediaStorageSOPInstanceUID = generate_uid()
        sc.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian

        sc.SOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
        sc.SOPInstanceUID = sc.file_meta.MediaStorageSOPInstanceUID
        sc.Modality = "OT"
        sc.Manufacturer = "DICOM Segmentation Backend"
        sc.SeriesDescription = "AI Segmentation Overlay"
        sc.ConversionType = "WSD"

        for attr in ("PatientName", "PatientID", "PatientBirthDate", "PatientSex",
                     "StudyInstanceUID", "StudyDate", "StudyTime", "StudyDescription",
                     "StudyID", "AccessionNumber", "FrameOfReferenceUID",
                     "ImagePositionPatient", "ImageOrientationPatient", "PixelSpacing",
                     "SliceThickness", "SliceLocation"):
            if hasattr(src_ds, attr):
                setattr(sc, attr, getattr(src_ds, attr))

        sc.SeriesInstanceUID = sc_series_uid
        sc.SeriesNumber = 998
        sc.InstanceNumber = slice_idx + 1

        sc.Rows, sc.Columns = rgb.shape[:2]
        sc.SamplesPerPixel = 3
        sc.PhotometricInterpretation = "RGB"
        sc.PlanarConfiguration = 0
        sc.BitsAllocated = 8
        sc.BitsStored = 8
        sc.HighBit = 7
        sc.PixelRepresentation = 0
        sc.PixelData = rgb.tobytes()

        captures.append(sc)

    logger.info("Created %d Secondary Capture images", len(captures))
    return captures


def create_dicom_seg(
    result: SegmentationResult,
    source_datasets: list[Dataset],
) -> Dataset:
    """Create a DICOM SEG object from a segmentation result using highdicom.

    Args:
        result: SegmentationResult with mask (D, H, W) and labels dict.
        source_datasets: pydicom Datasets of the original images (with pixel data).

    Returns:
        highdicom Segmentation dataset.
    """
    import highdicom as hd
    from highdicom.seg import (
        Segmentation,
        SegmentDescription,
        SegmentAlgorithmTypeEnum,
        SegmentationTypeEnum,
    )
    from highdicom.sr.coding import CodedConcept

    segment_descriptions = []
    for label_id in sorted(result.labels.keys()):
        if label_id == 0:
            continue
        name = result.labels[label_id]
        desc = SegmentDescription(
            segment_number=label_id,
            segment_label=name,
            segmented_property_category=CodedConcept(
                value="123037004",
                scheme_designator="SCT",
                meaning="Anatomical Structure",
            ),
            segmented_property_type=CodedConcept(
                value="51114001",
                scheme_designator="SCT",
                meaning="Artery",
            ),
            algorithm_type=SegmentAlgorithmTypeEnum.AUTOMATIC,
            algorithm_identification=hd.AlgorithmIdentificationSequence(
                name="DICOM Segmentation Backend",
                version="0.1.0",
            ),
        )
        segment_descriptions.append(desc)

    if not segment_descriptions:
        raise ValueError("No non-background labels in segmentation result")

    label_ids = sorted(k for k in result.labels if k != 0)
    mask_stack = np.stack(
        [(result.mask == lid).astype(np.uint8) for lid in label_ids],
        axis=0,
    )
    mask_4d = np.moveaxis(mask_stack, 0, -1)

    seg = Segmentation(
        source_images=source_datasets,
        pixel_array=mask_4d,
        segmentation_type=SegmentationTypeEnum.BINARY,
        segment_descriptions=segment_descriptions,
        series_instance_uid=generate_uid(),
        series_number=997,
        sop_instance_uid=generate_uid(),
        instance_number=1,
        manufacturer="DICOM Segmentation Backend",
        manufacturer_model_name="nnU-Net/MONAI",
        software_versions="0.1.0",
        device_serial_number="AI_SEGMENT",
        series_description="AI Segmentation (SEG)",
    )

    logger.info("Created DICOM SEG with %d segments", len(segment_descriptions))
    return seg
