# src/docgen/dataset_info.py
#
# Utilities to extract basic information from a YOLO object detection dataset.
#
# Assumed structure under dataset_root:
#
#   dataset_root/
#       images/
#       labels/
#       classes.txt
#
# - Number of images: count files under images/ (non-recursive).
# - Number of objects per class: parse each label file in labels/:
#     each line: "<class_id> x_center y_center width height"
#   The first token is the class index; it is mapped to a class name
#   using classes.txt (line index -> class name).

import os
from typing import Any, Dict, List, Tuple

from .logging_utils import log_info, log_warning, log_error


# You can extend this list if needed
VALID_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
}


def _list_files(folder: str) -> List[str]:
    """
    List all files (not directories) directly under a folder.
    Non-recursive on purpose for predictability.
    """
    if not os.path.isdir(folder):
        return []
    files: List[str] = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            files.append(path)
    return files


def _count_images(images_dir: str) -> int:
    """
    Count image files under images_dir with known image extensions.
    """
    files = _list_files(images_dir)
    count = 0
    for path in files:
        _, ext = os.path.splitext(path)
        if ext.lower() in VALID_IMAGE_EXTENSIONS:
            count += 1
    return count


def _load_classes(classes_path: str) -> List[str]:
    """
    Load class names from classes.txt.
    Each non-empty line is treated as one class name.
    """
    if not os.path.isfile(classes_path):
        log_warning(f"classes.txt not found at '{classes_path}'. No class names will be available.")
        return []

    classes: List[str] = []
    with open(classes_path, "r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if not name:
                continue
            classes.append(name)

    if not classes:
        log_warning(f"classes.txt at '{classes_path}' is empty.")
    return classes


def _parse_label_line(line: str) -> Tuple[int, bool]:
    """
    Parse a YOLO label line and return (class_id, ok_flag).

    The expected format is:
        <class_id> x_center y_center width height [optional extra fields]

    If parsing fails, returns (-1, False).
    """
    stripped = line.strip()
    if not stripped:
        return -1, False

    parts = stripped.split()
    if len(parts) == 0:
        return -1, False

    try:
        class_id = int(parts[0])
        return class_id, True
    except ValueError:
        return -1, False


def _count_objects_per_class(labels_dir: str) -> Dict[int, int]:
    """
    Traverse all label files in labels_dir and count how many objects each
    class_id has.
    """
    if not os.path.isdir(labels_dir):
        log_warning(f"Labels directory not found at '{labels_dir}'. No objects will be counted.")
        return {}

    label_files = _list_files(labels_dir)
    class_counts: Dict[int, int] = {}

    for label_path in label_files:
        _, ext = os.path.splitext(label_path)
        # We expect YOLO labels to be plain text files; filter by extension .txt
        if ext.lower() != ".txt":
            continue

        try:
            with open(label_path, "r", encoding="utf-8") as f:
                for line in f:
                    class_id, ok = _parse_label_line(line)
                    if not ok:
                        continue
                    class_counts[class_id] = class_counts.get(class_id, 0) + 1
        except Exception as ex:
            log_warning(f"Could not read label file '{label_path}': {ex}")

    return class_counts


def extract_dataset_info(dataset_root: str) -> Dict[str, Any]:
    """
    Extract information from a YOLO-style dataset rooted at dataset_root.

    Returns a dictionary with keys:
        - 'dataset_root': str
        - 'images_dir': str
        - 'labels_dir': str
        - 'classes_path': str
        - 'num_images': int
        - 'num_label_files': int
        - 'num_objects': int
        - 'classes': List[str]
        - 'class_counts_by_index': Dict[int, int]
        - 'class_counts_by_name': Dict[str, int]
    """
    images_dir = os.path.join(dataset_root, "images")
    labels_dir = os.path.join(dataset_root, "labels")
    classes_path = os.path.join(dataset_root, "classes.txt")

    if not os.path.isdir(dataset_root):
        log_error(f"Dataset root directory '{dataset_root}' does not exist.")
    else:
        log_info(f"Analysing dataset under '{dataset_root}'...")

    if not os.path.isdir(images_dir):
        log_warning(f"Images directory not found at '{images_dir}'.")
    if not os.path.isdir(labels_dir):
        log_warning(f"Labels directory not found at '{labels_dir}'.")

    # Count images
    num_images = _count_images(images_dir)

    # Count objects per class_id
    class_counts_by_index = _count_objects_per_class(labels_dir)
    num_objects = sum(class_counts_by_index.values())

    # Load class names
    classes = _load_classes(classes_path)

    # Map indices to names
    class_counts_by_name: Dict[str, int] = {}
    for class_id, count in class_counts_by_index.items():
        if 0 <= class_id < len(classes):
            class_name = classes[class_id]
        else:
            # Handle missing class names gracefully
            class_name = f"__missing_class_{class_id}__"
            log_warning(
                f"Found annotations for class_id {class_id}, "
                "which is out of range for classes.txt. Using placeholder name "
                f"'{class_name}'."
            )
        class_counts_by_name[class_name] = class_counts_by_name.get(class_name, 0) + count

    # Number of label files (can be useful to spot mismatches with num_images)
    num_label_files = len(
        [
            p
            for p in _list_files(labels_dir)
            if os.path.splitext(p)[1].lower() == ".txt"
        ]
    )

    info: Dict[str, Any] = {
        "dataset_root": dataset_root,
        "images_dir": images_dir,
        "labels_dir": labels_dir,
        "classes_path": classes_path,
        "num_images": num_images,
        "num_label_files": num_label_files,
        "num_objects": num_objects,
        "classes": classes,
        "class_counts_by_index": class_counts_by_index,
        "class_counts_by_name": class_counts_by_name,
    }

    log_info(
        f"Dataset summary: {num_images} images, "
        f"{num_label_files} label files, {num_objects} objects."
    )

    if classes:
        log_info(
            f"Detected {len(classes)} classes from classes.txt: "
            + ", ".join(classes)
        )

    return info
