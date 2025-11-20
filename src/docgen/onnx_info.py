# src/docgen/onnx_info.py
#
# Utilities to extract basic technical information from an ONNX model:
# - Input names, shapes and data types
# - Output names, shapes and data types
# - Approximate number of parameters (sum of elements in initializers)

import os
from typing import Any, Dict, List

import onnx
from onnx import TensorProto

from .logging_utils import log_info, log_warning, log_error


# Mapping from ONNX TensorProto data types to human-readable strings
DTYPE_MAP = {
    TensorProto.FLOAT: "float32",
    TensorProto.UINT8: "uint8",
    TensorProto.INT8: "int8",
    TensorProto.UINT16: "uint16",
    TensorProto.INT16: "int16",
    TensorProto.INT32: "int32",
    TensorProto.INT64: "int64",
    TensorProto.BOOL: "bool",
    TensorProto.FLOAT16: "float16",
    TensorProto.DOUBLE: "float64",
    TensorProto.UINT32: "uint32",
    TensorProto.UINT64: "uint64",
    TensorProto.COMPLEX64: "complex64",
    TensorProto.COMPLEX128: "complex128",
    TensorProto.BFLOAT16: "bfloat16",
}


def _tensor_type_to_dict(value_info: Any) -> Dict[str, Any]:
    """
    Convert an ONNX ValueInfoProto (input or output) into a dict with:
        - 'name'
        - 'dtype'
        - 'shape' (list of ints or strings for dynamic dims)
    """
    tensor_type = value_info.type.tensor_type
    elem_type = tensor_type.elem_type
    dtype = DTYPE_MAP.get(elem_type, f"UNKNOWN({elem_type})")

    shape: List[Any] = []
    for dim in tensor_type.shape.dim:
        if dim.dim_value is not None and dim.dim_value != 0:
            shape.append(int(dim.dim_value))
        elif dim.dim_param:
            shape.append(str(dim.dim_param))
        else:
            shape.append("?")

    return {
        "name": value_info.name,
        "dtype": dtype,
        "shape": shape,
    }


def _count_parameters(graph: Any) -> int:
    """
    Approximate number of parameters as the total number of elements
    in all graph initializers.
    """
    total = 0
    for initializer in graph.initializer:
        num_elements = 1
        if initializer.dims:
            for d in initializer.dims:
                num_elements *= int(d)
        total += num_elements
    return int(total)


def extract_onnx_info(model_path: str) -> Dict[str, Any]:
    """
    Extract basic technical information from an ONNX model.

    Returns a dictionary with keys:
        - 'model_path': str
        - 'inputs': List[Dict[str, Any]]
        - 'outputs': List[Dict[str, Any]]
        - 'num_parameters': int
    """
    info: Dict[str, Any] = {
        "model_path": model_path,
        "inputs": [],
        "outputs": [],
        "num_parameters": 0,
    }

    if not os.path.isfile(model_path):
        log_error(f"ONNX model file not found at '{model_path}'.")
        return info

    try:
        model = onnx.load(model_path)
        onnx.checker.check_model(model)
    except Exception as ex:
        log_error(f"Failed to load or validate ONNX model '{model_path}': {ex}")
        return info

    graph = model.graph

    # Inputs
    inputs: List[Dict[str, Any]] = []
    for value_info in graph.input:
        # Skip weights that might also appear as graph inputs in some exports
        inputs.append(_tensor_type_to_dict(value_info))

    # Outputs
    outputs: List[Dict[str, Any]] = []
    for value_info in graph.output:
        outputs.append(_tensor_type_to_dict(value_info))

    # Parameter count
    num_parameters = _count_parameters(graph)

    info["inputs"] = inputs
    info["outputs"] = outputs
    info["num_parameters"] = num_parameters

    log_info(
        f"ONNX model loaded from '{model_path}'. "
        f"Detected {len(inputs)} inputs, {len(outputs)} outputs, "
        f"approximately {num_parameters} parameters."
    )

    return info
