# ML Model Deployment Platform

A lightweight web-based platform for deploying machine learning models with auto-generated Gradio interfaces, containerized with Docker for security and isolation.

## 🎯 Overview

This platform allows users to:
- Upload ML models (sklearn, PyTorch, ONNX)
- Upload a configuration file specifying model behavior
- Automatically generate an interactive Gradio web interface
- Deploy in isolated Docker containers with resource limits
- Receive a public URL to access the deployed model

## 🏗 Architecture

```
project/
│
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config_validator.py  # Configuration validation
│   ├── app_generator.py     # Dynamic Gradio app generation
│   ├── docker_manager.py    # Container lifecycle management
│   ├── storage/             # Storage directories
│   │   ├── uploads/         # Temporary upload storage
│   │   └── containers/      # Container working directories
│   └── docker/
│       └── Dockerfile.template  # Docker image template
│
├── frontend/
│   └── index.html           # Web interface with iframe support
│
├── example_config.json      # Example configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker installed and running
- pip package manager

### Installation

1. Clone or navigate to the project directory
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Server

```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`

### Using the Web Interface

Open `frontend/index.html` in your browser to access the web interface:

- Upload model and configuration files
- View deployed models
- Open Gradio interfaces in embedded iframes
- Stop running containers

The frontend communicates with the backend API at `http://localhost:8000`.

## 📋 Configuration Schema

The `config.json` file must follow this schema:

```json
{
  "framework": "sklearn | pytorch | onnx",
  "task": "classification | regression",
  "input": {
    "type": "numeric | text | image",
    "features": 4  // Required for numeric type
  },
  "output": {
    "type": "label | number | text"
  }
}
```

### Framework-Extension Mapping

| Framework | Model Extension |
|-----------|----------------|
| sklearn   | .pkl          |
| pytorch   | .pt           |
| onnx      | .onnx         |

### Task-Output Compatibility

| Task          | Valid Output Types |
|---------------|-------------------|
| classification | label            |
| regression    | number            |

## 🧪 Testing with cURL

### Example 1: sklearn Classification Model

Create a test model first:
```python
# test_model.py - Run this to create a sample model
from sklearn.ensemble import RandomForestClassifier
import joblib

# Create sample model
model = RandomForestClassifier(n_estimators=10, random_state=42)
X = [[1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6], [4, 5, 6, 7]]
y = [0, 1, 0, 1]
model.fit(X, y)

# Save model
joblib.dump(model, "test_model.pkl")
print("Model saved as test_model.pkl")
```

Then deploy:
```bash
curl -X POST http://localhost:8000/deploy-model \
  -F "model_file=@test_model.pkl" \
  -F "config_file=@example_config.json"
```

### Example 2: Different Configurations

**Numeric Regression (sklearn):**
```json
{
  "framework": "sklearn",
  "task": "regression",
  "input": { "type": "numeric", "features": 3 },
  "output": { "type": "number" }
}
```

**Text Classification (PyTorch):**
```json
{
  "framework": "pytorch",
  "task": "classification",
  "input": { "type": "text" },
  "output": { "type": "label" }
}
```

**Image Classification (ONNX):**
```json
{
  "framework": "onnx",
  "task": "classification",
  "input": { "type": "image" },
  "output": { "type": "label" }
}
```

## 🔌 API Endpoints

### Health Check
```
GET /health
```

### Deploy Model
```
POST /deploy-model
Content-Type: multipart/form-data

Parameters:
  - model_file: Model file (.pkl, .pt, .onnx)
  - config_file: JSON configuration file

Response:
{
  "status": "success",
  "container_id": "abc123...",
  "url": "http://localhost:7861",
  "framework": "sklearn",
  "task": "classification"
}
```

### Stop Container
```
DELETE /containers/{container_id}
```

## 🔒 Security Features

- **No arbitrary code execution**: Only model files and configs are accepted
- **Non-root containers**: Docker containers run as unprivileged user
- **Network isolation**: Containers run with `--network none`
- **Resource limits**: 
  - Memory: 512MB per container
  - CPU: 0.5 cores per container
- **Input validation**: Strict schema validation for configurations

## 🐳 Docker Configuration

Each deployment creates:
1. Unique container directory
2. Dockerfile from template
3. Isolated image with minimal dependencies
4. Container with security constraints

### Resource Limits Applied
```bash
--memory 512m
--cpu-quota 50000  # 0.5 CPU cores
--network none     # No network access
```

## 📊 Monitoring

The platform logs:
- Container creation and startup
- Build progress
- Deployment status
- Errors and warnings

View logs in console output or integrate with your logging solution.

## 🔧 Troubleshooting

### Docker not available
```
Error: Docker is not available
```
Ensure Docker Desktop or Docker Engine is running on your system.

### Invalid config
```
Error: Config validation failed
```
Check your config.json against the schema requirements.

### Model loading errors
Ensure your model file matches the specified framework extension.

## 📝 Development

### Module Structure

**config_validator.py**: Validates JSON configs, checks framework-extension compatibility, ensures task-output consistency.

**app_generator.py**: Dynamically generates Gradio application code based on config:
- Maps input types to Gradio components
- Generates framework-specific loading code
- Creates prediction functions

**docker_manager.py**: Manages container lifecycle:
- Creates container directories
- Builds images
- Runs containers with security constraints
- Handles cleanup

**main.py**: FastAPI entry point orchestrating the entire deployment flow.

## 📜 License

This is an MVP implementation for demonstration purposes.

## 🚧 Future Enhancements

- Authentication and authorization
- Container auto-cleanup after timeout
- Model versioning
- Monitoring dashboard
- Multi-model support per container
- GPU support for deep learning models
