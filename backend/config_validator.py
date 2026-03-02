"""
Config Validator Module
Validates ML model deployment configurations against strict schema requirements.
Ensures framework-model compatibility and input/output specification correctness.
"""

import json
import os
from typing import Dict, Any, Tuple
from fastapi import HTTPException

# Valid framework and extension mappings
# PyTorch supports both .pt (TorchScript/full model) and .pth (checkpoint/state-dict)
FRAMEWORK_EXTENSIONS = {
    "sklearn": {".pkl"},
    "pytorch": {".pt", ".pth"},
    "onnx": {".onnx"}
}

VALID_FRAMEWORKS = set(FRAMEWORK_EXTENSIONS.keys())
VALID_TASKS = {"classification", "regression"}
VALID_INPUT_TYPES = {"numeric", "text", "image"}
VALID_OUTPUT_TYPES = {"label", "number", "text"}


def validate_config(config_data: Dict[str, Any], model_filename: str) -> Tuple[bool, str]:
    """
    Validate configuration JSON against strict schema.
    
    Args:
        config_data: Parsed JSON configuration dictionary
        model_filename: Name of the uploaded model file (for extension validation)
    
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    # Check required top-level fields
    required_fields = {"framework", "task", "input", "output"}
    missing_fields = required_fields - set(config_data.keys())
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate framework
    framework = config_data.get("framework")
    if framework not in VALID_FRAMEWORKS:
        return False, f"Invalid framework '{framework}'. Must be one of: {', '.join(VALID_FRAMEWORKS)}"
    
    # Validate framework matches model file extension
    allowed_extensions = FRAMEWORK_EXTENSIONS[framework]
    file_ext = os.path.splitext(model_filename.lower())[1]
    if file_ext not in allowed_extensions:
        ext_str = ', '.join(sorted(allowed_extensions))
        return False, f"Framework '{framework}' requires model file with extension in [{ext_str}], got '{file_ext}'"
    
    # Validate task
    task = config_data.get("task")
    if task not in VALID_TASKS:
        return False, f"Invalid task '{task}'. Must be one of: {', '.join(VALID_TASKS)}"
    
    # Validate input specification
    input_spec = config_data.get("input")
    if not isinstance(input_spec, dict):
        return False, "Input must be an object with 'type' and optional 'features'"
    
    if "type" not in input_spec:
        return False, "Input must specify 'type' field"
    
    input_type = input_spec.get("type")
    if input_type not in VALID_INPUT_TYPES:
        return False, f"Invalid input type '{input_type}'. Must be one of: {', '.join(VALID_INPUT_TYPES)}"
    
    # Validate numeric features count for numeric input type
    if input_type == "numeric":
        if "features" not in input_spec:
            return False, "Numeric input type requires 'features' field specifying feature count"
        
        features = input_spec.get("features")
        if not isinstance(features, int) or features < 1:
            return False, f"Invalid features count '{features}'. Must be a positive integer"
    
    # Validate output specification
    output_spec = config_data.get("output")
    if not isinstance(output_spec, dict):
        return False, "Output must be an object with 'type' field"
    
    if "type" not in output_spec:
        return False, "Output must specify 'type' field"
    
    output_type = output_spec.get("type")
    if output_type not in VALID_OUTPUT_TYPES:
        return False, f"Invalid output type '{output_type}'. Must be one of: {', '.join(VALID_OUTPUT_TYPES)}"
    
    # Validate task-output compatibility
    if task == "regression" and output_type == "label":
        return False, "Regression task cannot have 'label' output type (use 'number')"
    
    if task == "classification" and output_type == "number":
        return False, "Classification task cannot have 'number' output type (use 'label')"
    
    return True, "Configuration valid"


def validate_config_or_raise(config_data: Dict[str, Any], model_filename: str) -> Dict[str, Any]:
    """
    Validate configuration and raise HTTPException on failure.
    
    Args:
        config_data: Parsed JSON configuration dictionary
        model_filename: Name of the uploaded model file
    
    Returns:
        The validated config data
    
    Raises:
        HTTPException: With 400 status code if validation fails
    """
    is_valid, error_message = validate_config(config_data, model_filename)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Config validation failed: {error_message}")
    return config_data


def parse_and_validate_config(config_content: str, model_filename: str) -> Dict[str, Any]:
    """
    Parse JSON config and validate it.
    
    Args:
        config_content: Raw JSON string from uploaded file
        model_filename: Name of the uploaded model file
    
    Returns:
        The parsed and validated config dictionary
    
    Raises:
        HTTPException: If JSON parsing fails or validation fails
    """
    try:
        config_data = json.loads(config_content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in config file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config file: {str(e)}")
    
    return validate_config_or_raise(config_data, model_filename)
