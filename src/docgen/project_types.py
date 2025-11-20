# src/docgen/project_types.py
#
# Internal configuration for different project types.
# This is used by the prompt builder to give the LLM
# more context and a better suggested structure.

from typing import Dict, Any, Optional, Tuple


# Main registry of project types.
# Keys here are "canonical" names; we will map user-provided strings to these.
PROJECT_TYPE_CONFIG: Dict[str, Dict[str, Any]] = {
    "license_plate_detection": {
        "display_name": "License Plate Detection",
        "short_code": "LPD",
        "description": (
            "This task is related to detecting license plates in the wild, "
            "in a variety of environments (day, night, urban, highway, etc.). "
            "Images can be RGB or grayscale. Night images are typically captured "
            "with an IR (infrared) sensor, so license plates may appear with "
            "very different contrast characteristics compared to daytime images."
        ),
        "data_notes": (
            "The input images often come from roadside or surveillance cameras. "
            "They may include motion blur, perspective distortions, glare, and "
            "partial occlusions. The detector is expected to output tight bounding "
            "boxes around license plates, regardless of the plate layout (e.g. "
            "single-line, double-line) as long as the plate is visible."
        ),
        "recommended_sections": [
            "Overview",
            "Model Architecture",
            "Dataset and Annotations",
            "Training Setup and Augmentations",
            "Performance Metrics",
            "Deployment and Integration",
            "Limitations and Known Failure Cases",
        ],
    },
    "character_detection": {
        "display_name": "Character Detection",
        "short_code": "CHD",
        "description": (
            "This task is related to detecting and localising characters on "
            "license plates in the wild. It typically operates on cropped "
            "regions produced by a plate detector for the same region."
        ),
        "data_notes": (
            "Input images are grayscale only. The training images are generated "
            "by taking the outputs of a license plate detector, cropping the "
            "detected plate region, and then applying a normalisation process. "
            "This normalisation usually includes affine transformations to "
            "correct inclinations or perspective, and contrast/brightness "
            "adjustments to emphasise the characters against the plate background."
        ),
        "recommended_sections": [
            "Overview",
            "Input Normalisation Pipeline",
            "Model Architecture for Character Detection",
            "Dataset (Cropped Plates) and Label Format",
            "Training Setup and Augmentations",
            "Performance Metrics (Per Character Type, if applicable)",
            "Integration with Plate Detector",
            "Limitations and Edge Cases",
        ],
    },
    "vehicle_detection": {
        "display_name": "Vehicle Detection",
        "short_code": "VD",
        "description": (
            "This task consists of detecting vehicles on the road and classifying "
            "their type (e.g. car, truck, bus, motorbike, van, etc.). "
            "The model is expected to handle varying viewpoints, distances, "
            "and traffic densities."
        ),
        "data_notes": (
            "Input images usually come from traffic or roadside cameras with a "
            "fixed viewpoint. The detector must cope with different vehicle "
            "sizes, occlusions, overlapping objects, and diverse lighting "
            "conditions. Each detection is associated with a vehicle type "
            "class label."
        ),
        "recommended_sections": [
            "Overview",
            "Vehicle Classes and Taxonomy",
            "Model Architecture",
            "Dataset Composition and Class Distribution",
            "Training Setup and Augmentations",
            "Performance Metrics (Per Vehicle Class)",
            "Deployment and Runtime Constraints",
            "Limitations and Challenging Scenarios",
        ],
    },
}


# Aliases / mappings from user-provided strings to canonical keys.
PROJECT_TYPE_ALIASES: Dict[str, str] = {
    # License Plate Detection
    "license_plate_detection": "license_plate_detection",
    "lp_detection": "license_plate_detection",
    "lp-detector": "license_plate_detection",
    "plate_detector": "license_plate_detection",
    "plate_detection": "license_plate_detection",

    # Character Detection
    "character_detection": "character_detection",
    "char_detection": "character_detection",
    "characters": "character_detection",

    # Vehicle Detection
    "vehicle_detection": "vehicle_detection",
    "vehicle-detector": "vehicle_detection",
    "vehicle_detection_model": "vehicle_detection",
    "vehicles": "vehicle_detection",
}


def _normalise_project_type(raw: str) -> str:
    """
    Normalise a user-provided project_type string:
    - lower-case
    - replace spaces with underscores
    - strip leading/trailing whitespace
    """
    return raw.strip().lower().replace(" ", "_")


def get_project_type_info(project_type: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Given a project_type string from the config, return:
        (canonical_key, config_dict)

    If the project type is unknown, returns (None, None).
    """
    if not project_type:
        return None, None

    norm = _normalise_project_type(project_type)
    canonical = PROJECT_TYPE_ALIASES.get(norm)
    if canonical is None:
        # As a fallback, if the normalised string is directly in PROJECT_TYPE_CONFIG
        if norm in PROJECT_TYPE_CONFIG:
            canonical = norm
        else:
            return None, None

    cfg = PROJECT_TYPE_CONFIG.get(canonical)
    if cfg is None:
        return None, None

    return canonical, cfg
