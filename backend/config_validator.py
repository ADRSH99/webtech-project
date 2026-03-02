"""
Config Validator Module
Validates ML model deployment configurations against strict schema requirements.
Ensures framework-model compatibility and input/output specification correctness.
"""

import json
import os
from typing import Dict, Any, Tuple, List, Optional
from pydantic import BaseModel, Field, validator
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


class InputSpec(BaseModel):
    type: str
    features: Optional[int] = None

    @validator("type")
    def validate_input_type(cls, v):
        if v not in VALID_INPUT_TYPES:
            raise ValueError(f"Invalid input type '{v}'. Must be one of: {', '.join(VALID_INPUT_TYPES)}")
        return v

class OutputSpec(BaseModel):
    type: str

    @validator("type")
    def validate_output_type(cls, v):
        if v not in VALID_OUTPUT_TYPES:
            raise ValueError(f"Invalid output type '{v}'. Must be one of: {', '.join(VALID_OUTPUT_TYPES)}")
        return v

class ConfigModel(BaseModel):
    framework: str
    task: str
    input: InputSpec
    output: OutputSpec

    @validator("framework")
    def validate_framework(cls, v):
        if v not in VALID_FRAMEWORKS:
            raise ValueError(f"Invalid framework '{v}'. Must be one of: {', '.join(VALID_FRAMEWORKS)}")
        return v

    @validator("task")
    def validate_task(cls, v):
        if v not in VALID_TASKS:
            raise ValueError(f"Invalid task '{v}'. Must be one of: {', '.join(VALID_TASKS)}")
        return v

def validate_config(config_data: Dict[str, Any], model_filename: str) -> Tuple[bool, str]:
    """
    Validate configuration JSON against strict schema using Pydantic.
    """
    try:
        config = ConfigModel(**config_data)
        
        # Cross-field validation (framework/extension)
        allowed_extensions = FRAMEWORK_EXTENSIONS[config.framework]
        file_ext = os.path.splitext(model_filename.lower())[1]
        if file_ext not in allowed_extensions:
            ext_str = ', '.join(sorted(allowed_extensions))
            return False, f"Framework '{config.framework}' requires model file with extension in [{ext_str}], got '{file_ext}'"
        
        # Numeric input requirement
        if config.input.type == "numeric" and (config.input.features is None or config.input.features < 1):
            return False, "Numeric input type requires 'features' field specifying feature count"
        
        # Task-output compatibility
        if config.task == "regression" and config.output.type == "label":
            return False, "Regression task cannot have 'label' output type (use 'number')"
        
        if config.task == "classification" and config.output.type == "number":
            return False, "Classification task cannot have 'number' output type (use 'label')"
            
        return True, "Configuration valid"
    except Exception as e:
        return False, str(e)

def parse_and_validate_config(config_content: str, model_filename: str) -> Dict[str, Any]:
    """
    Parse JSON config and validate it using Pydantic.
    """
    try:
        config_data = json.loads(config_content)
        is_valid, error_message = validate_config(config_data, model_filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Config validation failed: {error_message}")
        return config_data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in config file: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing config file: {str(e)}")
