# ModelForge — Complete Line-by-Line Code Explanation

This document explains **every line of code** in the entire ModelForge project, organized by file.

---

# Backend Files

---

## 1. `backend/main.py` — FastAPI Entry Point (408 lines)

This is the central orchestrator. It receives HTTP requests, validates inputs, generates Gradio apps, deploys Docker containers, and manages authentication.

```python
"""
Main FastAPI Application
Entry point for the ML model deployment platform.
Handles file uploads, orchestrates validation, app generation, and deployment.
"""
```
**Lines 1–5:** Module docstring describing the file's purpose.

```python
import os                          # Operating system interface — file paths, environment variables
import tempfile                    # Creates temporary directories for processing uploads
import shutil                      # High-level file operations — copying, deleting directory trees
import asyncio                     # Async support (imported for potential future use)
from typing import Optional, List  # Type hints for function signatures
from contextlib import asynccontextmanager  # Enables async startup/shutdown lifecycle
```
**Lines 7–12:** Standard library imports used throughout the module.

```python
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
```
**Lines 14–15:** FastAPI framework imports:
- `FastAPI` — main application class
- `File` — marks a parameter as a file upload
- `UploadFile` — wrapper around uploaded files with filename, content type
- `HTTPException` — raises HTTP error responses (400, 401, 500, etc.)
- `Depends` — dependency injection for auth (injects `get_current_user` into endpoints)
- `CORSMiddleware` — handles Cross-Origin Resource Sharing headers

```python
from config_validator import parse_and_validate_config
from app_generator import generate_gradio_app, save_app_to_file
from docker_manager import DockerManager
from database import (
    init_db, add_deployment, get_all_deployments,
    remove_deployment, remove_all_deployments,
    add_user, get_user_by_username
)
from auth import hash_password, verify_password, create_token, get_current_user
from pydantic import BaseModel
```
**Lines 17–27:** Project module imports — each local module handles one responsibility (validation, Gradio generation, Docker, database, authentication). `BaseModel` from Pydantic is used for request/response schemas.

```python
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
DOCKER_DIR = os.getenv("DOCKER_DIR", "docker")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
CONTAINERS_DIR = os.path.join(STORAGE_DIR, "containers")
TEMPLATES_DIR = DOCKER_DIR
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024
ALLOWED_MODEL_EXTENSIONS = {".pkl", ".pt", ".pth", ".onnx"}
ALLOWED_CONFIG_EXTENSIONS = {".json"}
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:5173").split(",")
```
**Lines 29–38:** Configuration constants. All use `os.getenv()` with defaults so they can be overridden via environment variables. `MAX_FILE_SIZE` converts MB to bytes. The allowed extensions sets enforce which file types are accepted.

```python
class DeploymentResponse(BaseModel):
    status: str
    container_id: str
    url: str
    framework: str
    task: str

class ContainerInfo(BaseModel):
    id: int
    container_id: str
    internal_id: str
    model_name: str
    framework: str
    task: str
    host_port: Optional[int]
    url: Optional[str]
    status: str
    created_at: str

class AuthRequest(BaseModel):
    username: str
    password: str
```
**Lines 40–62:** Pydantic models defining the shape of API requests and responses. FastAPI uses these for automatic validation and OpenAPI documentation. `AuthRequest` is used by both `/auth/register` and `/auth/login`.

```python
def ensure_directories():
    """Ensure required directories exist."""
    for dir_path in [UPLOADS_DIR, CONTAINERS_DIR, TEMPLATES_DIR]:
        os.makedirs(dir_path, exist_ok=True)
```
**Lines 65–68:** Creates the required storage directories on startup. `exist_ok=True` means it won't error if they already exist.

```python
def validate_file_upload(file: UploadFile, allowed_extensions: set, max_size: int) -> None:
```
**Lines 71–99:** Validates uploaded files — checks that filename exists, extension is in the allowed set, and file size doesn't exceed the max. Raises `HTTPException` with 400 status on failure.

```python
docker_manager: Optional[DockerManager] = None
```
**Line 103:** Global variable holding the Docker manager instance. Initialized during startup, checked for `None` before use.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    ensure_directories()
    init_db()
    global docker_manager
    docker_manager = DockerManager(STORAGE_DIR, DOCKER_DIR)
    ...
    yield
    # Shutdown
    print("✓ Shutting down ML Deployment Platform")
```
**Lines 106–128:** The lifespan context manager runs code on app startup (before `yield`) and shutdown (after `yield`). It creates directories, initializes the SQLite database, and creates the Docker manager.

```python
app = FastAPI(
    title="ML Model Deployment Platform",
    description="Auto-generate Gradio interfaces for ML models with Docker isolation",
    version="1.0.0",
    lifespan=lifespan
)
```
**Lines 131–137:** Creates the FastAPI application instance with metadata for the auto-generated Swagger docs.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```
**Lines 139–146:** CORS middleware allows the React frontend (on port 5173) to make requests to the backend (on port 8000). Without this, browsers would block cross-origin requests.

```python
@app.get("/")
async def root():
    return {"status": "healthy", "service": "ML Model Deployment Platform", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    docker_available = docker_manager is not None and docker_manager.is_docker_available()
    return {"status": "healthy", "docker_available": docker_available, ...}
```
**Lines 149–167:** Two public health check endpoints. The `/health` endpoint also reports Docker availability.

```python
@app.post("/auth/register")
async def register(body: AuthRequest):
    if len(body.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    existing = get_user_by_username(body.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    hashed = hash_password(body.password)
    user_id = add_user(body.username, hashed)
    token = create_token(user_id, body.username)
    return {"status": "success", "token": token, "username": body.username}
```
**Lines 170–188:** Registration endpoint. Validates username length (≥3) and password length (≥6), checks for duplicate usernames (409 Conflict), hashes the password with bcrypt, saves to SQLite, creates a JWT token, and returns it.

```python
@app.post("/auth/login")
async def login(body: AuthRequest):
    user = get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(user["id"], user["username"])
    return {"status": "success", "token": token, "username": user["username"]}
```
**Lines 191–201:** Login endpoint. Looks up user in SQLite, verifies password hash with bcrypt, creates and returns a JWT token. Returns 401 if credentials are invalid.

```python
@app.post("/deploy-model")
async def deploy_model(
    model_file: UploadFile = File(...),
    config_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)   # <-- Auth required
):
```
**Lines 204–208:** Deployment endpoint, **protected by JWT**. `Depends(get_current_user)` extracts the token from the `Authorization: Bearer <token>` header and validates it. If invalid/missing, returns 401 automatically.

**Lines 222–324:** The deployment logic:
1. Validates file extensions and sizes
2. Creates a temp directory
3. Saves uploaded files to disk
4. Parses and validates the JSON config
5. Generates a Gradio app from the config
6. Calls `docker_manager.deploy()` to build and run the container
7. Saves deployment metadata to SQLite
8. Returns the container ID and URL
9. Cleans up the temp directory in `finally` block

```python
@app.get("/containers", response_model=List[ContainerInfo])
async def list_containers():
    deployments = get_all_deployments()
    return deployments
```
**Lines 327–339:** Lists all deployments from SQLite. **Public** (no auth required) so the dashboard can show containers.

```python
@app.delete("/containers/cleanup-all")
async def cleanup_all_containers(current_user: dict = Depends(get_current_user)):
    docker_manager.cleanup_all_containers()
    remove_all_deployments()
    return {"status": "success", "message": "All containers cleaned up"}
```
**Lines 342–359:** Stops all containers, removes all images and folders, and clears the database. **Protected by JWT.**

```python
@app.delete("/containers/{container_id}/cleanup")
async def cleanup_container(container_id: str, current_user: dict = Depends(get_current_user)):
    docker_manager.cleanup_container(container_id)
    remove_deployment(container_id)
```
**Lines 362–381:** Stops and cleans up a single container + removes its DB record. **Protected.**

```python
@app.delete("/containers/{container_id}")
async def stop_container(container_id: str, current_user: dict = Depends(get_current_user)):
    docker_manager.stop_container(container_id)
    remove_deployment(container_id)
```
**Lines 384–403:** Stops a single container + removes its DB record. **Protected.**

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
**Lines 406–408:** Entry point — starts the Uvicorn ASGI server on port 8000, accessible from any network interface.

---

## 2. `backend/auth.py` — Authentication Module (89 lines)

Handles password hashing, JWT token creation/verification, and the FastAPI dependency for protecting endpoints.

```python
import os       # For reading environment variables (JWT_SECRET, etc.)
import bcrypt   # Industry-standard password hashing library
import jwt      # PyJWT library for JSON Web Token operations
from datetime import datetime, timedelta, timezone  # Token expiry calculation
from typing import Optional, Dict, Any              # Type hints
```
**Lines 6–10:** Imports — `bcrypt` for password security, `jwt` for token management.

```python
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
```
**Lines 12–13:** FastAPI security utilities. `HTTPBearer` automatically extracts `Bearer <token>` from the `Authorization` header. `HTTPAuthorizationCredentials` holds the extracted token.

```python
JWT_SECRET = os.getenv("JWT_SECRET", "modelforge-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
```
**Lines 16–18:** JWT configuration. The secret key signs/verifies tokens. HS256 is HMAC-SHA256 (symmetric). Tokens expire after 24 hours by default.

```python
security = HTTPBearer()
```
**Line 21:** Creates the security scheme. When used with `Depends()`, FastAPI auto-extracts the Bearer token from request headers.

```python
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
```
**Lines 24–27:** Hashes a plaintext password. `gensalt()` creates a random salt. `hashpw()` combines salt + password into a bcrypt hash. Result is decoded to string for SQLite storage.

```python
def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
```
**Lines 30–32:** Compares a plaintext password against a stored bcrypt hash. Returns True/False. bcrypt internally extracts the salt from the hash.

```python
def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),       # "subject" — standard JWT claim for user ID
        "username": username,       # Custom claim for display name
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),  # Expiry time
        "iat": datetime.now(timezone.utc),  # "issued at" — when the token was created
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
```
**Lines 35–52:** Creates a JWT token with the user's ID, username, and expiry. `jwt.encode()` signs the payload with the secret key using HS256.

```python
def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```
**Lines 55–77:** Decodes and verifies a JWT token. `jwt.decode()` checks the signature and expiry automatically. Raises 401 if expired or tampered with.

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    payload = decode_token(credentials.credentials)
    return {"user_id": int(payload["sub"]), "username": payload["username"]}
```
**Lines 80–88:** FastAPI dependency function. When used as `Depends(get_current_user)` on an endpoint, FastAPI:
1. Extracts the `Authorization: Bearer <token>` header via `HTTPBearer`
2. Passes the token to `decode_token()` for verification
3. Returns the user info dict to the endpoint function

---

## 3. `backend/config_validator.py` — Configuration Validation (109 lines)

Validates the JSON configuration that specifies how a model should be served.

```python
FRAMEWORK_EXTENSIONS = {
    "sklearn": {".pkl"},
    "pytorch": {".pt", ".pth"},
    "onnx": {".onnx"}
}
```
**Lines 15–19:** Maps each ML framework to its valid file extensions. Used to verify that the uploaded model file matches the declared framework.

```python
VALID_FRAMEWORKS = set(FRAMEWORK_EXTENSIONS.keys())  # {"sklearn", "pytorch", "onnx"}
VALID_TASKS = {"classification", "regression"}
VALID_INPUT_TYPES = {"numeric", "text", "image"}
VALID_OUTPUT_TYPES = {"label", "number", "text"}
```
**Lines 21–24:** Allowed values for each config field.

```python
class InputSpec(BaseModel):
    type: str
    features: Optional[int] = None

    @validator("type")
    def validate_input_type(cls, v):
        if v not in VALID_INPUT_TYPES:
            raise ValueError(...)
        return v
```
**Lines 27–35:** Pydantic model for the `input` section. `features` is optional (only required for numeric inputs). The `@validator` decorator runs when the model is instantiated and rejects invalid types.

```python
class OutputSpec(BaseModel):
    type: str

    @validator("type")
    def validate_output_type(cls, v):
        ...
```
**Lines 37–44:** Pydantic model for the `output` section with type validation.

```python
class ConfigModel(BaseModel):
    framework: str
    task: str
    input: InputSpec
    output: OutputSpec

    @validator("framework")
    def validate_framework(cls, v): ...

    @validator("task")
    def validate_task(cls, v): ...
```
**Lines 46–62:** Top-level config Pydantic model. Nested models (`InputSpec`, `OutputSpec`) are validated automatically. Framework and task validators check against allowed sets.

```python
def validate_config(config_data: Dict[str, Any], model_filename: str) -> Tuple[bool, str]:
    config = ConfigModel(**config_data)  # Pydantic validates all fields
    # Cross-field: framework vs file extension
    allowed_extensions = FRAMEWORK_EXTENSIONS[config.framework]
    file_ext = os.path.splitext(model_filename.lower())[1]
    if file_ext not in allowed_extensions:
        return False, f"Framework '{config.framework}' requires..."
    # Numeric input needs features count
    if config.input.type == "numeric" and (config.input.features is None or config.input.features < 1):
        return False, "Numeric input type requires 'features' field..."
    # Task-output compatibility
    if config.task == "regression" and config.output.type == "label":
        return False, "Regression task cannot have 'label' output type"
    if config.task == "classification" and config.output.type == "number":
        return False, "Classification task cannot have 'number' output type"
    return True, "Configuration valid"
```
**Lines 64–91:** The main validation function. Performs three levels of checks:
1. **Schema validation** — Pydantic (field types, allowed values)
2. **Cross-field validation** — framework must match model file extension
3. **Semantic validation** — task type must be compatible with output type

```python
def parse_and_validate_config(config_content: str, model_filename: str) -> Dict[str, Any]:
    config_data = json.loads(config_content)
    is_valid, error_message = validate_config(config_data, model_filename)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Config validation failed: {error_message}")
    return config_data
```
**Lines 93–108:** Entry point called from `main.py`. Parses JSON string, validates it, and either returns the config dict or raises an HTTP 400 error.

---

## 4. `backend/app_generator.py` — Dynamic Gradio App Generation (307 lines)

Generates a complete Python script that loads a model, creates a prediction function, and launches a Gradio web interface.

```python
def generate_gradio_app(config: Dict[str, Any], model_filename: str) -> str:
    framework = config["framework"]
    task = config["task"]
    input_spec = config["input"]
    output_spec = config["output"]
    imports = _generate_imports(framework)
    model_loading = _generate_model_loading(framework, model_filename)
    prediction_fn = _generate_prediction_function(framework, task, input_spec, output_spec)
    interface_code = _generate_interface(input_spec, output_spec, prediction_fn)
    ...
```
**Lines 11–61:** Main function that orchestrates code generation by calling four helper functions and combining their outputs into a complete Python script.

```python
def _generate_imports(framework: str) -> str:
    base_imports = "import gradio as gr\nimport numpy as np\n"
    if framework == "sklearn":
        return base_imports + "import joblib\n"
    elif framework == "pytorch":
        return base_imports + "import torch\nimport torch.nn as nn\n"
    elif framework == "onnx":
        return base_imports + "import onnxruntime as ort\n"
```
**Lines 64–75:** Generates framework-specific import statements. All frameworks need `gradio` and `numpy`.

```python
def _generate_model_loading(framework: str, model_filename: str) -> str:
```
**Lines 78–116:** Generates model loading code:
- **sklearn**: `joblib.load(MODEL_PATH)`
- **pytorch**: `torch.load(MODEL_PATH, map_location='cpu', weights_only=False)` with fallback for older PyTorch
- **onnx**: `ort.InferenceSession(MODEL_PATH)`

Each includes error handling and status logging.

```python
def _generate_prediction_function(framework, task, input_spec, output_spec) -> str:
```
**Lines 119–239:** Generates the `predict()` function. This is the most complex generator because it handles:
- **Input preprocessing**: numeric (single/multiple features), text, or image inputs
- **Framework-specific inference**: sklearn `predict`/`predict_proba`, PyTorch `model(tensor)` with `torch.no_grad()`, ONNX `session.run()`
- **Output formatting**: dict of labels→probabilities for classification, float for regression

```python
def _generate_interface(input_spec, output_spec, prediction_fn) -> str:
```
**Lines 242–294:** Generates the Gradio `Interface` configuration:
- Maps input types to Gradio components: `gr.Number` (numeric), `gr.Textbox` (text), `gr.Image` (image)
- Maps output types: `gr.Label` (classification), `gr.Number` (regression), `gr.Textbox` (text)
- Launches on `0.0.0.0:7860` (accessible from outside the container)

```python
def save_app_to_file(app_code: str, output_path: str) -> None:
    with open(output_path, 'w') as f:
        f.write(app_code)
```
**Lines 297–306:** Writes the generated Python code to a file.

---

## 5. `backend/docker_manager.py` — Container Lifecycle Management (524 lines)

Manages the entire Docker lifecycle: creating directories, building images, running containers with resource limits, health polling, and cleanup.

```python
BASE_IMAGE = "python:3.10-slim"
CONTAINER_MEMORY_LIMIT = "512m"
CONTAINER_CPU_LIMIT = 0.5
CONTAINER_PORT = 7860
NETWORK_MODE = "bridge"
```
**Lines 25–29:** Docker configuration constants. `bridge` network mode enables port mapping so Gradio can be accessed from the host.

```python
class DockerManager:
    def __init__(self, storage_dir: str, docker_dir: str):
        self.containers_dir = Path(storage_dir) / "containers"
        self.templates_dir = Path(docker_dir)
        self.client = None
        self.containers_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as e:
            self.client = None
```
**Lines 32–63:** Constructor initializes the Docker client from environment (Docker socket). If Docker isn't available, sets `client` to `None` and logs a warning instead of crashing.

```python
    def create_container_folder(self) -> str:
        container_id = str(uuid.uuid4())[:8]
        container_path = self.containers_dir / container_id
        container_path.mkdir(parents=True, exist_ok=True)
        return container_id
```
**Lines 74–85:** Creates a unique 8-character directory for each deployment's files.

```python
    def copy_model_files(self, container_id, model_path, config_path, app_path, model_filename):
        container_path = self.containers_dir / container_id
        shutil.copy2(model_path, container_path / model_filename)
        shutil.copy2(config_path, container_path / "config.json")
        shutil.copy2(app_path, container_path / "app.py")
```
**Lines 87–112:** Copies the three required files (model, config, generated app.py) into the container's build directory.

```python
    def create_dockerfile(self, container_id, framework, model_filename):
        template = open(template_path).read()
        framework_deps = {"sklearn": "scikit-learn joblib", "pytorch": "torch torchvision", "onnx": "onnxruntime"}
        dockerfile_content = template.format(base_image=..., framework_deps=..., port=..., model_filename=...)
```
**Lines 114–157:** Reads the Dockerfile template, substitutes framework-specific dependencies, and writes the final Dockerfile.

```python
    def build_image(self, container_id):
        image, build_logs = self.client.images.build(path=..., tag=f"ml-deploy-{container_id}", rm=True, forcerm=True)
```
**Lines 159–199:** Builds a Docker image from the container directory. `rm=True` removes intermediate containers after build.

```python
    def run_container(self, image_tag, labels=None):
        container = self.client.containers.run(
            image=image_tag,
            detach=True,
            ports={f'{CONTAINER_PORT}/tcp': None},  # Auto-assign host port
            mem_limit=CONTAINER_MEMORY_LIMIT,
            cpu_quota=int(CONTAINER_CPU_LIMIT * 100000),
            network_mode=NETWORK_MODE,
            remove=True,  # Auto-remove on stop
            labels=container_labels
        )
```
**Lines 201–293:** Runs the container with security constraints:
- `detach=True` — runs in background
- `ports` with `None` — Docker auto-assigns a host port
- `mem_limit="512m"` — 512 MB memory cap
- `cpu_quota=50000` — 0.5 CPU cores
- `remove=True` — container auto-deletes when stopped

Then retrieves the assigned host port from Docker's port bindings.

```python
    def wait_for_container_ready(self, host_port, timeout=90):
        url = f"http://localhost:{host_port}"
        while time.time() < deadline:
            resp = http_requests.get(url, timeout=3)
            if resp.status_code == 200:
                return True
            time.sleep(3)
        return False
```
**Lines 295–319:** Polls the Gradio endpoint every 3 seconds until it responds with HTTP 200, up to 90 seconds (to account for pip install time inside the container).

```python
    def deploy(self, model_path, config_path, app_path, framework):
```
**Lines 321–390:** Full deployment pipeline: create folder → copy files → create Dockerfile → build image → run container → wait for ready → return result dict.

```python
    def cleanup_container(self, container_id):
```
**Lines 392–426:** Stops running containers, removes Docker images, and deletes the container directory.

```python
    def cleanup_all_containers(self):
```
**Lines 428–472:** Finds all containers with label `ml-deploy=true`, stops and removes them, removes all `ml-deploy-*` images, and deletes all container directories.

```python
    def stop_container(self, container_id):
        container = self.client.containers.get(container_id)
        container.stop(timeout=10)
```
**Lines 511–523:** Stops a single container by its Docker ID.

---

## 6. `backend/database.py` — SQLite Database Operations (136 lines)

Manages persistent storage for deployments and user accounts.

```python
DB_PATH = "model_forge.db"
```
**Line 6:** Database file path. SQLite creates this file automatically.

```python
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS deployments (...)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (...)''')
    conn.commit()
    conn.close()
```
**Lines 8–40:** Creates both tables if they don't exist:
- **deployments**: `id, container_id, internal_id, model_name, framework, task, host_port, url, status, created_at`
- **users**: `id, username (UNIQUE), password_hash, created_at`

```python
def add_deployment(container_id, internal_id, model_name, framework, task, host_port, url):
    cursor.execute('INSERT INTO deployments (...) VALUES (?, ?, ?, ?, ?, ?, ?)', (...))
```
**Lines 42–61:** Inserts a new deployment record. Uses parameterized queries (`?`) to prevent SQL injection.

```python
def get_all_deployments() -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row  # Enables dict-like access to rows
    cursor.execute('SELECT * FROM deployments ORDER BY created_at DESC')
    return [dict(row) for row in rows]
```
**Lines 63–74:** Fetches all deployments sorted by newest first. `row_factory = sqlite3.Row` makes results accessible by column name.

```python
def remove_deployment(container_id): ...
def remove_all_deployments(): ...
def update_status(container_id, status): ...
```
**Lines 76–104:** Standard CRUD operations — delete by ID, delete all, update status.

```python
def add_user(username: str, password_hash: str) -> int:
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (...))
    return cursor.lastrowid

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    return dict(row) if row else None
```
**Lines 109–135:** User functions. `add_user` returns the auto-incremented ID. `get_user_by_username` returns `None` if not found (used by login to check credentials).

---

## 7. `backend/docker/Dockerfile.template` — Container Image Template (43 lines)

Template that gets variable substitution at build time.

```dockerfile
FROM {base_image}                    # python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1        # Don't create .pyc files
ENV PYTHONUNBUFFERED=1               # Print output immediately (no buffering)
ENV PIP_NO_CACHE_DIR=1               # Don't cache pip downloads (smaller image)
RUN groupadd -r appuser && useradd -r -g appuser appuser  # Create non-root user
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc  # C compiler for some Python packages
RUN pip install --no-cache-dir gradio>=4.0.0 numpy>=1.0.0 pillow>=10.0.0 {framework_deps}
COPY app.py .
COPY config.json .
COPY {model_filename} .
RUN chown -R appuser:appuser /app    # Make appuser owner of all files
USER appuser                         # Switch to non-root user (security)
EXPOSE {port}                        # Document that port 7860 is used
CMD ["python", "app.py"]             # Run the Gradio app
```

---

# Frontend Files

---

## 8. `frontend/src/App.jsx` — Main React Component (492 lines)

The single-page application with login/register flow and model management dashboard.

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, RefreshCw, Trash2, ExternalLink, CheckCircle2, AlertCircle, Activity, Clock, LogOut, LogIn, X } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
```
**Lines 1–17:** React hooks (`useState` for state, `useEffect` for side effects on mount), Axios HTTP client, Lucide icon components, and Tailwind class utilities (`clsx` for conditional classes, `twMerge` for deduplication).

```jsx
function cn(...inputs) {
  return twMerge(clsx(inputs));
}
```
**Lines 19–21:** Utility function combining `clsx` (conditional class names) and `twMerge` (resolves conflicting Tailwind classes like `text-red-500` vs `text-blue-500`).

```jsx
const API_BASE = 'http://localhost:8000';
```
**Line 23:** Backend API base URL.

```jsx
const authHeaders = () => {
  const token = localStorage.getItem('mf_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};
```
**Lines 26–29:** Helper function that returns auth headers for protected API calls. Reads the JWT token from `localStorage`.

```jsx
const [token, setToken] = useState(localStorage.getItem('mf_token'));
const [username, setUsername] = useState(localStorage.getItem('mf_user') || '');
const [authMode, setAuthMode] = useState('login');
const [authForm, setAuthForm] = useState({ username: '', password: '' });
const [authError, setAuthError] = useState(null);
const [authLoading, setAuthLoading] = useState(false);
```
**Lines 33–38:** Auth-related state. Token persists in `localStorage` so the user stays logged in across page refreshes.

```jsx
const [deployments, setDeployments] = useState([]);
const [loading, setLoading] = useState(false);
const [refreshing, setRefreshing] = useState(false);
const [message, setMessage] = useState(null);
const [selectedModelUrl, setSelectedModelUrl] = useState(null);
const [healthStatus, setHealthStatus] = useState(null);
```
**Lines 41–46:** Application state — deployment list, loading indicators, status messages, selected model for iframe display, Docker health status.

```jsx
const handleAuth = async (e) => {
    e.preventDefault();
    const endpoint = authMode === 'register' ? '/auth/register' : '/auth/login';
    const resp = await axios.post(`${API_BASE}${endpoint}`, authForm);
    const { token: jwt, username: user } = resp.data;
    localStorage.setItem('mf_token', jwt);
    localStorage.setItem('mf_user', user);
    setToken(jwt);
    setUsername(user);
};
```
**Lines 49–67:** Auth form submission. Sends username/password to either register or login endpoint. On success, stores the JWT token in `localStorage` and updates React state.

```jsx
const handleLogout = () => {
    localStorage.removeItem('mf_token');
    localStorage.removeItem('mf_user');
    setToken(null);
};
```
**Lines 69–75:** Logout — clears token from `localStorage` and state, which triggers the login screen.

```jsx
useEffect(() => {
    fetchDeployments();
    checkHealth();
}, []);
```
**Lines 99–102:** `useEffect` with empty dependency array runs once on component mount — fetches the deployment list and Docker health status.

```jsx
const resp = await axios.post(`${API_BASE}/deploy-model`, formData, {
    headers: authHeaders(),
});
```
**Lines 123–125:** Deploy request sends the auth token via `Authorization: Bearer <token>` header.

```jsx
await axios.delete(`${API_BASE}/containers/${containerId}`, {
    headers: authHeaders(),
});
```
**Lines 140–142:** Stop container request also includes auth headers.

```jsx
if (!token) {
    return ( /* Login/Register UI */ );
}
```
**Lines 164–250:** Conditional rendering — if no token is stored, the entire UI shows the login/register form instead of the dashboard. The form has:
- Tab toggle between Login and Register modes
- Username and password inputs with validation
- Error display for failed auth attempts
- Loading spinner during auth request

```jsx
return ( /* Main Dashboard */ );
```
**Lines 253–489:** The authenticated dashboard, containing:
- **Header** (lines 255–288): Logo, Docker status indicator, username display, logout button
- **Deploy form** (lines 294–338): File upload inputs for model and config, deploy button with loading state, status messages
- **Deployments grid** (lines 342–438): Cards showing model name, framework, task, status, port, container ID, and creation timestamp
- **iFrame viewer** (lines 443–478): Embedded Gradio interface with header showing container info, fullscreen and close buttons

---

## 9. `frontend/src/main.jsx` — React Entry Point (11 lines)

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- **Line 1:** Imports React library
- **Line 2:** Imports ReactDOM for browser rendering
- **Line 3:** Imports the main App component
- **Line 4:** Imports global CSS (Tailwind directives)
- **Lines 6–9:** Creates a React root attached to the `<div id="root">` element in `index.html`, renders the `App` component wrapped in `StrictMode` (enables extra development warnings)

---

## 10. `frontend/src/index.css` — Global Styles (25 lines)

```css
@tailwind base;        /* Reset and base styles from Tailwind */
@tailwind components;  /* Component classes from Tailwind */
@tailwind utilities;   /* Utility classes (text-lg, flex, etc.) */

:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;  /* Google Fonts Inter with fallbacks */
  line-height: 1.5;                    /* Default line height */
  font-weight: 400;                    /* Default normal weight */
  font-synthesis: none;                /* Prevent browser from synthesizing bold/italic */
  text-rendering: optimizeLegibility;  /* Improve text rendering quality */
  -webkit-font-smoothing: antialiased; /* Smooth fonts on WebKit browsers */
  -moz-osx-font-smoothing: grayscale;  /* Smooth fonts on Firefox/macOS */
}

body {
  margin: 0;          /* Remove default body margin */
  min-width: 320px;   /* Minimum supported width */
  min-height: 100vh;  /* Full viewport height */
}

#root {
  width: 100%;  /* React root takes full width */
}
```

---

## 11. `frontend/index.html` — HTML Entry Point (18 lines)

```html
<!DOCTYPE html>                               <!-- HTML5 doctype -->
<html lang="en">                              <!-- Language attribute for accessibility -->
<head>
  <meta charset="UTF-8" />                    <!-- UTF-8 character encoding -->
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />  <!-- Responsive viewport -->
  <title>ModelForge | ML Model UI Platform</title>  <!-- Browser tab title -->
  <link rel="preconnect" href="https://fonts.googleapis.com">      <!-- Preconnect to Google Fonts CDN -->
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>  <!-- Preconnect to font file CDN -->
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">  <!-- Load Inter font weights -->
</head>
<body>
  <div id="root"></div>                       <!-- React mount point -->
  <script type="module" src="/src/main.jsx"></script>  <!-- ES module entry point -->
</body>
</html>
```

---

# Configuration Files

---

## 12. `frontend/tailwind.config.js` — Tailwind Configuration (28 lines)

```js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",     // Scan all source files for Tailwind class usage
  ],
  theme: {
    extend: {
      colors: {
        primary: {                       // Custom blue color palette
          50: '#f0f9ff',                 // Lightest
          100: '#e0f2fe',
          ...
          600: '#0284c7',                // Main brand color (buttons, accents)
          ...
          950: '#082f49',                // Darkest
        },
      },
    },
  },
  plugins: [],
}
```

The `content` array tells Tailwind which files to scan for class names (so unused classes are purged in production). The custom `primary` color palette extends the default theme.

---

## 13. `frontend/vite.config.js` — Vite Configuration (8 lines)

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],     // Enables JSX transformation and React Fast Refresh (HMR)
})
```

Minimal Vite config — the React plugin handles JSX compilation and enables hot module replacement during development.

---

## 14. `frontend/package.json` — NPM Dependencies (35 lines)

**Dependencies** (shipped to users):
- `axios` — HTTP client for API calls
- `clsx` — Conditional CSS class names
- `lucide-react` — SVG icon components
- `react` / `react-dom` — React 19 framework
- `tailwind-merge` — Deduplicates Tailwind classes

**Dev Dependencies** (build tools only):
- `@vitejs/plugin-react` — Vite React plugin
- `autoprefixer` — Adds vendor prefixes to CSS
- `postcss` — CSS processing pipeline
- `tailwindcss` — Utility CSS framework
- `vite` — Build tool and dev server
- `eslint` — Code linting

---

## 15. `requirements.txt` — Python Dependencies (32 lines)

```
fastapi>=0.104.0          # Web framework
uvicorn[standard]>=0.24.0 # ASGI server (runs FastAPI)
python-multipart>=0.0.6   # File upload support for FastAPI
docker>=6.1.0             # Docker SDK for Python
scikit-learn>=1.3.0       # ML framework (sklearn models)
torch>=2.1.0              # ML framework (PyTorch models)
onnxruntime>=1.16.0       # ML framework (ONNX models)
gradio>=4.0.0             # UI generation library
pydantic>=2.0.0           # Data validation schemas
requests>=2.31.0          # HTTP client (health polling)
pyjwt>=2.8.0              # JWT token creation/verification
bcrypt>=4.0.0             # Password hashing
numpy>=1.24.0             # Array operations
pillow>=10.0.0            # Image processing
joblib>=1.3.0             # Model serialization (sklearn)
```

---

## 16. `tests/generate_test_models.py` — Test Model Generator (141 lines)

```python
def create_sklearn_classifier():
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    X = np.array([[5.1, 3.5, 1.4, 0.2], ...])  # Iris-like features
    y = [0, 0, 1, 1, 0, 1]                       # Binary labels
    model.fit(X, y)
    joblib.dump(model, "test_classifier.pkl")
    # Also creates the matching config JSON
```
**Lines 12–54:** Creates a RandomForest classifier with 4 features and 6 samples, saves as `.pkl` with a matching config.

```python
def create_sklearn_regressor():
    model = LinearRegression()
    X = np.array([[1,2,3], [2,3,4], ...])         # 3 features
    y = [10.0, 15.0, 20.0, 25.0, 30.0]            # Continuous targets
    model.fit(X, y)
    joblib.dump(model, "test_regressor.pkl")
```
**Lines 57–98:** Creates a LinearRegression model with 3 features, saves as `.pkl` with config.

```python
def test_prediction(model_path, sample_input):
    model = joblib.load(model_path)
    prediction = model.predict([sample_input])
    print(f"  Sample prediction for {sample_input}: {prediction[0]}")
```
**Lines 101–106:** Loads a saved model and runs a test prediction to verify it works.

**Lines 109–141:** Main block creates both models, runs test predictions, and prints cURL commands for deploying them.

---

## 17. `example_config.json` — Example Configuration (12 lines)

```json
{
  "framework": "sklearn",        // ML framework used
  "task": "classification",      // Prediction task type
  "input": {
    "type": "numeric",           // Input data type
    "features": 4                // Number of numeric features
  },
  "output": {
    "type": "label"              // Output type (classification → label)
  }
}
```

---

# Manual Verification Steps

## Prerequisites
- Python 3.10+ with virtualenv
- Docker Desktop or Docker Engine installed and running
- Node.js 18+ with npm

## Step-by-Step Verification

### 1. Activate the virtual environment
```bash
cd /home/adarsh/Documents/webtechproj
source venv/bin/activate
```

### 2. Delete old database (to create fresh users table)
```bash
cd webtech-project/backend
rm -f model_forge.db
```

### 3. Start the backend
```bash
cd webtech-project/backend
python main.py
```
**Expected:** Console shows `✓ ML Deployment Platform started`, `✓ SQLite database initialized`, `✓ Docker manager initialized successfully`.

### 4. Test health endpoint
Open a **new terminal** and run:
```bash
curl http://localhost:8000/health
```
**Expected:** `{"status":"healthy","docker_available":true,"docker_status":"connected"}`

### 5. Test authentication (register)
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'
```
**Expected:** `{"status":"success","token":"eyJ...","username":"testuser"}`

### 6. Test authentication (login)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}'
```
**Expected:** `{"status":"success","token":"eyJ...","username":"testuser"}`

### 7. Test protected endpoint without token
```bash
curl -X POST http://localhost:8000/deploy-model \
  -F "model_file=@tests/test_classifier.pkl" \
  -F "config_file=@tests/test_classifier_config.json"
```
**Expected:** `{"detail":"Not authenticated"}` (HTTP 403)

### 8. Test model deployment WITH token
Save the token from step 5/6, then:
```bash
TOKEN="eyJ..."  # paste the token here
curl -X POST http://localhost:8000/deploy-model \
  -H "Authorization: Bearer $TOKEN" \
  -F "model_file=@tests/test_classifier.pkl" \
  -F "config_file=@tests/test_classifier_config.json"
```
**Expected:** `{"status":"success","container_id":"...","url":"http://localhost:XXXXX","framework":"sklearn","task":"classification"}`

### 9. Open the Gradio interface
Open the URL from step 8 in your browser. Enter 4 numbers (e.g., `5.1, 3.5, 1.4, 0.2`) and click Submit.
**Expected:** Classification result with probabilities.

### 10. Start the frontend
In a **new terminal**:
```bash
cd webtech-project/frontend
npm run dev
```
Open `http://localhost:5173` in your browser.

### 11. Test frontend login flow
1. **Register**: Enter a username (≥3 chars) and password (≥6 chars) → click "Create Account"
2. **Expected**: Dashboard appears with model deployment form and Docker status indicator
3. **Verify**: Your username appears in the top-right header with a logout button

### 12. Test frontend deployment
1. Click "Deploy New Model"
2. Select `tests/test_classifier.pkl` as Model File
3. Select `tests/test_classifier_config.json` as Config File
4. Click "Deploy to Container"
5. **Expected**: Success message, deployment card appears with framework badge, task badge, status, port, and timestamp

### 13. Test iframe viewer
1. Click on the deployment card
2. **Expected**: Gradio interface loads in the embedded iframe below the cards

### 14. Test container stop
1. Hover over the deployment card → click the trash icon
2. Confirm the dialog
3. **Expected**: Card disappears, container is stopped

### 15. Test logout
1. Click the logout icon in the top-right
2. **Expected**: Login screen appears, token is cleared from localStorage
