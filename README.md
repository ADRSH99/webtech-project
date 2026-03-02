# ModelForge 🚀

A powerful, lightweight web-based platform for deploying machine learning models with **auto-generated Gradio interfaces**, secured by **JWT authentication** and isolated with **Docker containers**.

## 🎯 Overview

ModelForge abstracts away the complexity of ML deployment. Simply upload your model and a configuration file, and the platform handles:
- **Auto-UI Generation**: Creates a full Gradio interface based on your model's task (Classification/Regression).
- **Secure Isolation**: Runs each model in a separate Docker container with strict resource limits.
- **Persistent Management**: Tracks all deployments in a SQLite database.
- **Access Control**: JWT-based authentication ensures only authorized users can deploy or manage models.

## 🏗 Project Structure

```
webtech-project/
├── backend/
│   ├── main.py              # FastAPI orchestrator
│   ├── auth.py              # JWT + bcrypt security
│   ├── config_validator.py  # Pydantic schema validation
│   ├── app_generator.py     # Dynamic Gradio code generation
│   ├── docker_manager.py    # Docker SDK lifecycle management
│   └── database.py          # SQLite persistence layer
├── frontend/
│   ├── src/                 # React source (App.jsx, main.jsx)
│   ├── tailwind.config.js   # UI Design System
│   └── vite.config.js       # Fast build configuration
├── tests/                   # Sample models and test scripts
└── v3_modelforge.md         # Full project report
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker Desktop or Docker Engine installed and running

### 1. Backend Setup
```bash
# It is recommended to use the virtualenv provided in the parent directory
source ../venv/bin/activate
cd backend

# Install dependencies if not already done
pip install -r ../requirements.txt

# Start the API server
python main.py
```
*The API will be available at `http://localhost:8000`*

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
*Access the dashboard at `http://localhost:5173`*

## 🔐 Authentication Flow

ModelForge uses a stateless JWT authentication system:
1. **Register/Login**: Users create an account or sign in through the dashboard.
2. **Token Storage**: A JWT token is stored in `localStorage`.
3. **Protected Actions**: Deploying, stopping, or cleaning up containers requires the token to be sent in the `Authorization` header.
4. **Security**: Passwords are never stored in plaintext (secured with `bcrypt`).

## 📋 Configuration Schema

Each model requires a `config.json` to define its interface:

```json
{
  "framework": "sklearn | pytorch | onnx",
  "task": "classification | regression",
  "input": {
    "type": "numeric | text | image",
    "features": 4  // Required for numeric
  },
  "output": {
    "type": "label | number | text"
  }
}
```

## 🧪 Testing

We provide pre-trained sample models in the `tests/` directory.

**Quick Test via cURL (Requires Auth Token):**
```bash
# 1. Login to get token
# 2. Deploy sample classifier
curl -X POST http://localhost:8000/deploy-model \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -F "model_file=@tests/test_classifier.pkl" \
  -F "config_file=@tests/test_classifier_config.json"
```

## 🔒 Security Features

- **Container Isolation**: Each model runs in its own sandbox.
- **Resource Limits**: 512MB RAM and 0.5 CPU core maximum per container.
- **Non-Root Guard**: Containers execute as an unprivileged `appuser`.
- **JWT Protection**: destructive API endpoints are gated behind token validation.
- **Input Sanitization**: Strict Pydantic validation on all uploaded configurations.

## 🛠 Modules

- **`main.py`**: The central FastAPI hub.
- **`auth.py`**: Manages registration, login, and token verification.
- **`app_generator.py`**: The logic engine that "writes" Python code for the model UI.
- **`docker_manager.py`**: Builds images from templates and manages container state.
- **`database.py`**: SQLite adapter for deployment and user data.

## 📜 Project Documentation

For deeper details, refer to:
- [V3 Project Report](v3_modelforge.md)
- [Line-by-Line Code Explanation](explanations.md)

---
*Developed for the Web Technologies and Applications (IT254) course.*
