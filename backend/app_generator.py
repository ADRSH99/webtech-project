"""
App Generator Module
Dynamically generates Gradio application code based on model configuration.
Creates framework-specific model loading and input/output component mapping.
"""

import os
from typing import Dict, Any


def generate_gradio_app(config: Dict[str, Any], model_filename: str) -> str:
    """
    Generate a complete Gradio application Python script.
    
    Args:
        config: Validated configuration dictionary
        model_filename: Name of the model file to load
    
    Returns:
        Python code string for the Gradio application
    """
    framework = config["framework"]
    task = config["task"]
    input_spec = config["input"]
    output_spec = config["output"]
    
    # Generate imports section
    imports = _generate_imports(framework)
    
    # Generate model loading code
    model_loading = _generate_model_loading(framework, model_filename)
    
    # Generate task variable
    task_variable = f'task = "{task}"'
    
    # Generate prediction function
    prediction_fn = _generate_prediction_function(framework, task, input_spec, output_spec)
    
    # Generate Gradio interface components
    interface_code = _generate_interface(input_spec, output_spec, prediction_fn)
    
    # Combine all sections
    app_code = f'''"""
Auto-generated Gradio application for ML model deployment.
Framework: {framework}
Task: {task}
"""

{imports}

# Model loading
{model_loading}

# Task configuration
{task_variable}

{prediction_fn}

{interface_code}
'''
    return app_code


def _generate_imports(framework: str) -> str:
    """Generate framework-specific imports."""
    base_imports = "import gradio as gr\nimport numpy as np\n"
    
    if framework == "sklearn":
        return base_imports + "import joblib\n"
    elif framework == "pytorch":
        return base_imports + "import torch\nimport torch.nn as nn\n"
    elif framework == "onnx":
        return base_imports + "import onnxruntime as ort\n"
    else:
        return base_imports


def _generate_model_loading(framework: str, model_filename: str) -> str:
    """Generate model loading code based on framework."""
    if framework == "sklearn":
        return f'''MODEL_PATH = "{model_filename}"
try:
    model = joblib.load(MODEL_PATH)
    print(f"✓ Model loaded successfully from {{MODEL_PATH}}")
except Exception as e:
    print(f"✗ Failed to load model: {{e}}")
    raise'''
    
    elif framework == "pytorch":
        return f'''MODEL_PATH = "{model_filename}"
try:
    # weights_only=False is set explicitly to support full model objects (not just state dicts).
    # Use weights_only=True and load a state dict if you control the serialisation process.
    try:
        model = torch.load(MODEL_PATH, map_location=torch.device('cpu'), weights_only=False)
    except TypeError:
        # Fallback for PyTorch < 1.13 that does not have the weights_only parameter
        model = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    model.eval()
    print(f"✓ Model loaded successfully from {{MODEL_PATH}}")
except Exception as e:
    print(f"✗ Failed to load model: {{e}}")
    raise'''
    
    elif framework == "onnx":
        return f'''MODEL_PATH = "{model_filename}"
try:
    session = ort.InferenceSession(MODEL_PATH)
    input_name = session.get_inputs()[0].name
    print(f"✓ Model loaded successfully from {{MODEL_PATH}}")
except Exception as e:
    print(f"✗ Failed to load model: {{e}}")
    raise'''
    
    else:
        return f'# Unknown framework: {framework}\nmodel = None'


def _generate_prediction_function(
    framework: str, 
    task: str, 
    input_spec: Dict[str, Any], 
    output_spec: Dict[str, Any]
) -> str:
    """Generate the prediction function based on configuration."""
    input_type = input_spec["type"]
    output_type = output_spec["type"]
    
    # Generate input processing based on type
    if input_type == "numeric":
        features_count = input_spec.get("features", 1)
        if features_count == 1:
            # Single numeric feature
            preprocess = """    # Convert single input to numpy array
    input_data = np.array([[input_value]], dtype=np.float32)"""
            fn_signature = "input_value"
        else:
            # Multiple numeric features - expect list
            error_msg = f'Error: Expected {features_count} features, got '
            preprocess = f"""    # Convert list of inputs to numpy array
    input_data = np.array([input_values], dtype=np.float32)
    if input_data.shape[1] != {features_count}:
        return "{error_msg}" + str(input_data.shape[1])"""
            fn_signature = "*input_values"
    
    elif input_type == "text":
        preprocess = """    # Text input preprocessing
    input_data = input_text"""
        fn_signature = "input_text"
    
    elif input_type == "image":
        preprocess = """    # Image preprocessing
    import PIL.Image as Image
    if isinstance(input_image, np.ndarray):
        input_image = Image.fromarray(input_image)
    # Convert to numpy array and normalize
    input_data = np.array(input_image.resize((224, 224)))  # Standard resize
    input_data = input_data.astype(np.float32) / 255.0
    input_data = np.transpose(input_data, (2, 0, 1))  # HWC to CHW
    input_data = np.expand_dims(input_data, axis=0)"""
        fn_signature = "input_image"
    
    else:
        preprocess = "    input_data = input_value"
        fn_signature = "input_value"
    
    # Generate framework-specific prediction and properly formatted output.
    # For classification tasks, gr.Label expects a dict {label: confidence} or a plain label.
    # For regression tasks, gr.Number expects a float.
    if framework == "sklearn":
        if task == "classification":
            predict_code = """    # sklearn classification prediction
    prediction = model.predict(input_data)
    if hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(input_data)[0]
        classes = model.classes_ if hasattr(model, 'classes_') else range(len(probabilities))
        return {str(cls): float(prob) for cls, prob in zip(classes, probabilities)}
    return str(prediction[0])"""
        else:
            predict_code = """    # sklearn regression prediction
    prediction = model.predict(input_data)
    return float(prediction[0])"""
    
    elif framework == "pytorch":
        if task == "classification":
            predict_code = """    # PyTorch classification prediction
    with torch.no_grad():
        if isinstance(input_data, np.ndarray):
            input_tensor = torch.from_numpy(input_data)
        else:
            input_tensor = input_data
        output = model(input_tensor)
        probabilities = torch.softmax(output, dim=1).numpy()[0]
    return {str(i): float(p) for i, p in enumerate(probabilities)}"""
        else:
            predict_code = """    # PyTorch regression prediction
    with torch.no_grad():
        if isinstance(input_data, np.ndarray):
            input_tensor = torch.from_numpy(input_data)
        else:
            input_tensor = input_data
        output = model(input_tensor)
    return float(output.numpy().flatten()[0])"""
    
    elif framework == "onnx":
        if task == "classification":
            predict_code = """    # ONNX classification prediction
    if isinstance(input_data, np.ndarray):
        ort_input = {input_name: input_data}
    else:
        ort_input = {input_name: np.array([input_data], dtype=np.float32)}
    outputs = session.run(None, ort_input)
    raw_probs = outputs[0][0]
    # Softmax if logits (values > 1 indicate raw logits)
    if raw_probs.max() > 1.0:
        exp_v = np.exp(raw_probs - raw_probs.max())
        raw_probs = exp_v / exp_v.sum()
    return {str(i): float(p) for i, p in enumerate(raw_probs)}"""
        else:
            predict_code = """    # ONNX regression prediction
    if isinstance(input_data, np.ndarray):
        ort_input = {input_name: input_data}
    else:
        ort_input = {input_name: np.array([input_data], dtype=np.float32)}
    outputs = session.run(None, ort_input)
    return float(outputs[0].flatten()[0])"""
    
    else:
        predict_code = "    return 'Unknown framework'"
    
    return f'''def predict({fn_signature}):
    """
    Make prediction using loaded model.
    {f"Expects {input_spec.get('features', 1)} numeric features" if input_type == "numeric" else f"Expects {input_type} input"}
    Returns a dict {{label: confidence}} for classification, or a float for regression.
    """
{preprocess}

{predict_code}'''


def _generate_interface(
    input_spec: Dict[str, Any], 
    output_spec: Dict[str, Any],
    prediction_fn: str
) -> str:
    """Generate Gradio interface code."""
    input_type = input_spec["type"]
    output_type = output_spec["type"]
    
    # Generate input components
    if input_type == "numeric":
        features_count = input_spec.get("features", 1)
        if features_count == 1:
            inputs = 'gr.Number(label="Input Value")'
            fn_call = "predict"
        else:
            # Create multiple number inputs
            inputs = "[\n"
            for i in range(features_count):
                inputs += f'        gr.Number(label="Feature {i+1}"),\n'
            inputs += "    ]"
            fn_call = "lambda *args: predict(*args)"
    
    elif input_type == "text":
        inputs = 'gr.Textbox(label="Input Text", lines=3)'
        fn_call = "predict"
    
    elif input_type == "image":
        inputs = 'gr.Image(label="Input Image", type="numpy")'
        fn_call = "predict"
    
    else:
        inputs = 'gr.Textbox(label="Input")'
        fn_call = "predict"
    
    # Generate output components
    if output_type == "label":
        outputs = 'gr.Label(label="Prediction")'
    elif output_type == "number":
        outputs = 'gr.Number(label="Prediction")'
    else:  # text
        outputs = 'gr.Textbox(label="Output", lines=2)'
    
    return f'''# Launch Gradio interface
if __name__ == "__main__":
    demo = gr.Interface(
        fn={fn_call},
        inputs={inputs},
        outputs={outputs},
        title="ML Model Inference",
        description="Auto-generated interface for ML model deployment"
    )
    demo.launch(server_name="0.0.0.0", server_port=7860)'''


def save_app_to_file(app_code: str, output_path: str) -> None:
    """
    Save generated app code to file.
    
    Args:
        app_code: Generated Python code string
        output_path: Path where to save the file
    """
    with open(output_path, 'w') as f:
        f.write(app_code)
