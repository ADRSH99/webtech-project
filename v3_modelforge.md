# ModelForge: A Platform for Rapid AI Model UI Generation (V3)

**Project Course:** IT254 Web Technologies and Applications

**Authors:** Adarsh Bellamane, Yash Roshan, Jatin Tolani

---

## Abstract

ModelForge is a lightweight web-based platform that enables users to upload machine learning models and automatically generate interactive web interfaces for them. The system leverages Gradio for UI generation, FastAPI for backend services, Docker for secure execution, SQLite for persistent metadata storage, and JWT-based authentication for access control. The primary objective of the project is to reduce the effort required to deploy and demonstrate machine learning models by abstracting away frontend and deployment complexity.

**Index Terms:** Machine Learning Deployment, Gradio, FastAPI, Docker, JWT Authentication, SQLite, React, Web Interfaces

---

## I. Introduction

Machine learning models are frequently developed in research and academic environments, but deploying these models for interactive use often requires extensive engineering effort and DevOps knowledge. This includes frontend development, API design, dependency management, and runtime configuration.

ModelForge addresses this challenge by providing a unified system that automatically converts machine learning models into browser-accessible applications. Users simply upload a trained model and a configuration file, and the platform handles everything else — from generating the UI to containerizing and serving the model securely.

---

## II. Existing Problems

Despite the rapid growth of machine learning, several challenges exist in deploying models for real-world or academic demonstrations:

- Model deployment often requires knowledge of frontend frameworks and web technologies.
- Setting up inference APIs and UI pipelines is time-consuming and repetitive.
- Executing third-party or user-uploaded models poses security and isolation risks.
- Many existing deployment platforms are complex and unsuitable for academic projects.
- Lack of authentication means anyone with the URL can deploy or control models.
- No persistent tracking of deployed models across server restarts.

---

## III. Innovation and Contribution

ModelForge introduces a minimal yet effective approach to model deployment by combining existing tools in a novel academic-oriented workflow. The key innovations of this project include:

- **Automatic UI generation** — Interactive model interfaces are generated using Gradio without any manual frontend development.
- **Configuration-driven deployment** — A simple JSON config file specifies framework, task type, input/output specifications.
- **Container-based isolation** — User-uploaded models execute inside Docker containers with resource limits (512 MB memory, 0.5 CPU cores).
- **Non-root container execution** — Docker images run as unprivileged users for security.
- **JWT authentication** — Users must register and login before deploying or managing models. Tokens are verified on every protected API call.
- **Persistent metadata** — SQLite stores deployment records and user accounts, surviving server restarts.
- **Lightweight architecture** — Avoids unnecessary infrastructure complexity while providing production-grade security features.
- **Models as interactive web apps** — Deployed models are accessible through auto-generated Gradio interfaces embedded in iframes, not just raw APIs.

---

## IV. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend                      │
│   (Login/Register → Dashboard → iFrame Viewer)       │
│              Vite + Tailwind CSS                     │
└────────────────────┬────────────────────────────────┘
                     │ HTTP (Axios + JWT Bearer Token)
                     ▼
┌─────────────────────────────────────────────────────┐
│                FastAPI Backend                        │
│                                                      │
│  /auth/register  /auth/login       (Public)          │
│  /health         /containers GET   (Public)          │
│  /deploy-model   /containers DELETE (Protected)      │
│                                                      │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │   auth.py   │ │config_valid. │ │app_generator │  │
│  │ (bcrypt+JWT)│ │ (Pydantic)   │ │  (Gradio)    │  │
│  └─────────────┘ └──────────────┘ └──────────────┘  │
│  ┌─────────────┐ ┌──────────────┐                    │
│  │ database.py │ │docker_manager│                    │
│  │  (SQLite)   │ │  (Docker SDK)│                    │
│  └─────────────┘ └──────────────┘                    │
└────────────────────┬────────────────────────────────┘
                     │ Docker API
                     ▼
┌─────────────────────────────────────────────────────┐
│            Docker Containers                         │
│  ┌───────────────────────────────────────────────┐   │
│  │  python:3.10-slim + Gradio + Model            │   │
│  │  Non-root user │ 512 MB │ 0.5 CPU │ Port 7860 │   │
│  └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## V. Methodology

The system workflow operates as follows:

1. **Authentication** — User registers or logs in via the React frontend. The backend validates credentials (bcrypt hashing) and returns a JWT token.
2. **Model Upload** — The authenticated user uploads a trained ML model file (.pkl, .pt, .onnx) along with a JSON configuration file through the web interface.
3. **Validation** — The backend validates the configuration using Pydantic schemas, checking framework-extension compatibility and task-output consistency.
4. **App Generation** — Based on the configuration, the system dynamically generates a complete Gradio Python application with framework-specific model loading and prediction code.
5. **Containerization** — A Dockerfile is generated from a template, the model and app files are copied into a container directory, and a Docker image is built.
6. **Deployment** — The container is launched with resource limits (512 MB RAM, 0.5 CPU), and the system polls the Gradio endpoint until it becomes ready.
7. **Database Recording** — Deployment metadata (container ID, model name, framework, port, URL) is saved to SQLite.
8. **Interface Access** — The generated Gradio interface is embedded into the React frontend via an iframe, allowing seamless interaction through the browser.

---

## VI. Tools and Implementation

The implementation of ModelForge relies on widely used and well-supported technologies:

| Technology | Purpose |
|---|---|
| **Python 3.10** | Core backend language for API logic and model execution |
| **FastAPI** | Handles API endpoints, request validation, CORS, and auth middleware |
| **Pydantic** | Ensures data validation and schema enforcement for configs and auth requests |
| **Gradio** | Automatically generates interactive web interfaces for ML models |
| **Docker** | Provides isolated execution environments with resource limits |
| **SQLite** | Stores deployment metadata and user accounts persistently |
| **JWT (PyJWT)** | Stateless token-based authentication for protected endpoints |
| **bcrypt** | Industry-standard password hashing for secure credential storage |
| **React 19** | Frontend SPA framework with hooks for state management |
| **Vite** | Fast development server and production bundler |
| **Tailwind CSS 3** | Utility-first CSS framework for responsive UI styling |
| **Axios** | HTTP client for API communication with auth header injection |
| **Lucide React** | Icon library for consistent UI iconography |

### Project File Structure

```
webtech-project/
├── backend/
│   ├── main.py              # FastAPI entry point (408 lines)
│   ├── auth.py              # JWT + bcrypt authentication (89 lines)
│   ├── config_validator.py  # Pydantic config validation (109 lines)
│   ├── app_generator.py     # Dynamic Gradio app generation (307 lines)
│   ├── docker_manager.py    # Container lifecycle management (524 lines)
│   ├── database.py          # SQLite CRUD operations (136 lines)
│   ├── docker/
│   │   └── Dockerfile.template  # Container image template
│   └── storage/
│       ├── uploads/         # Temporary upload storage
│       └── containers/      # Container working directories
├── frontend/
│   ├── index.html           # HTML entry point with Google Fonts
│   ├── src/
│   │   ├── App.jsx          # Main React component (492 lines)
│   │   ├── main.jsx         # React DOM entry point
│   │   └── index.css        # Tailwind directives + base styles
│   ├── tailwind.config.js   # Custom color palette
│   ├── vite.config.js       # Vite + React plugin
│   └── package.json         # NPM dependencies
├── tests/
│   ├── generate_test_models.py  # Test model generator script
│   ├── test_classifier.pkl      # Sample sklearn classifier
│   ├── test_classifier_config.json
│   ├── test_regressor.pkl       # Sample sklearn regressor
│   └── test_regressor_config.json
├── requirements.txt         # Python dependencies
├── example_config.json      # Example configuration
└── README.md                # Project documentation
```

---

## VII. API Reference

### Public Endpoints (No Authentication Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root health check |
| GET | `/health` | Detailed health check (Docker status) |
| POST | `/auth/register` | Register a new user account |
| POST | `/auth/login` | Login and receive JWT token |
| GET | `/containers` | List all active deployments |

### Protected Endpoints (JWT Token Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/deploy-model` | Deploy a model with auto-generated UI |
| DELETE | `/containers/{id}` | Stop a running container |
| DELETE | `/containers/{id}/cleanup` | Stop + remove container files |
| DELETE | `/containers/cleanup-all` | Stop + remove all containers |

---

## VIII. Authentication Flow

1. User submits username + password to `/auth/register` or `/auth/login`.
2. Backend hashes password with bcrypt (register) or verifies against stored hash (login).
3. On success, a JWT token is created with a 24-hour expiry and returned to the frontend.
4. Frontend stores the token in `localStorage` and attaches it as `Authorization: Bearer <token>` to all protected API calls.
5. Backend extracts and verifies the token on protected endpoints using FastAPI's `Depends(get_current_user)` mechanism.
6. On logout, the token is removed from `localStorage`.

---

## IX. Security Features

- **JWT Authentication** — All destructive operations (deploy, stop, cleanup) require a valid token.
- **bcrypt Password Hashing** — Passwords are never stored in plaintext; bcrypt with random salt is used.
- **No Arbitrary Code Execution** — Only model files and JSON configs are accepted; no raw Python code execution.
- **Non-Root Containers** — Docker containers run as unprivileged `appuser`.
- **Resource Limits** — Each container is constrained to 512 MB memory and 0.5 CPU cores.
- **Input Validation** — Strict Pydantic schema validation for all configurations and auth requests.
- **Auto-Removal** — Containers are automatically removed when stopped (`--rm` flag).
- **CORS Configuration** — Only whitelisted origins can access the API.

---

## X. Configuration Schema

The `config.json` file must follow this schema:

```json
{
  "framework": "sklearn | pytorch | onnx",
  "task": "classification | regression",
  "input": {
    "type": "numeric | text | image",
    "features": 4
  },
  "output": {
    "type": "label | number | text"
  }
}
```

### Framework-Extension Mapping

| Framework | Model Extension |
|-----------|----------------|
| sklearn | .pkl |
| pytorch | .pt, .pth |
| onnx | .onnx |

### Task-Output Compatibility

| Task | Valid Output Types |
|------|-------------------|
| classification | label |
| regression | number |

---

## XI. Expected Results

The system allows users to deploy machine learning models within seconds and interact with them through automatically generated interfaces. ModelForge prioritizes ease of use, system stability, security through authentication, and clarity of design over large-scale performance optimization.

---

## XII. Applications

ModelForge can be applied in several scenarios:

- Academic project demonstrations and coursework submissions.
- Rapid prototyping of machine learning models.
- Hackathons and technical workshops.
- Internal tools for research teams.
- Teaching web technologies concepts (REST APIs, authentication, containerization).

---

## XIII. Conclusion

ModelForge demonstrates that effective machine learning deployment does not require complex infrastructure. By integrating FastAPI, Gradio, Docker, SQLite, and JWT authentication into a cohesive system, the project provides a practical and educational platform for rapid model deployment. The design emphasizes simplicity, security, and accessibility, making it well-suited for academic environments. The addition of JWT-based authentication elevates the project from a prototype to a production-aware application, demonstrating real-world security practices in a web technologies context.
