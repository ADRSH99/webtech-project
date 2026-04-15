"""
Main FastAPI Application
Entry point for the ML model deployment platform.
Handles file uploads, orchestrates validation, app generation, and deployment.
"""

import os
import tempfile
import shutil
import asyncio
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import modules
from config_validator import parse_and_validate_config
from app_generator import generate_gradio_app, save_app_to_file
from docker_manager import DockerManager
from database import (
    init_db, add_deployment, get_all_deployments,
    remove_deployment, remove_all_deployments,
    update_deployment_port, update_status,
    update_deployment_runtime,
    get_deployment_by_identifier, remove_deployment_by_identifier,
    add_user, get_user_by_username
)
from auth import hash_password, verify_password, create_token, get_current_user
from pydantic import BaseModel

# Configuration - paths relative to backend/ folder
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.getenv("STORAGE_DIR", os.path.join(BACKEND_DIR, "storage"))
DOCKER_DIR = os.getenv("DOCKER_DIR", os.path.join(BACKEND_DIR, "..", "docker"))
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
CONTAINERS_DIR = os.path.join(STORAGE_DIR, "containers")
TEMPLATES_DIR = DOCKER_DIR
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024  # 100MB default
ALLOWED_MODEL_EXTENSIONS = {".pkl", ".pt", ".pth", ".onnx"}
ALLOWED_CONFIG_EXTENSIONS = {".json"}
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080,http://localhost:5173").split(",")

# Pydantic models for responses
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


def _resolve_artifact_files(internal_id: str):
    """Resolve artifact folder paths and identify model file."""
    artifact_dir = os.path.join(CONTAINERS_DIR, internal_id)
    if not os.path.isdir(artifact_dir):
        raise HTTPException(status_code=404, detail=f"Artifact folder not found: {internal_id}")

    config_path = os.path.join(artifact_dir, "config.json")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=400, detail=f"config.json missing for artifact: {internal_id}")

    model_filename = None
    model_path = None
    for name in os.listdir(artifact_dir):
        ext = os.path.splitext(name)[1].lower()
        if ext in ALLOWED_MODEL_EXTENSIONS:
            model_filename = name
            model_path = os.path.join(artifact_dir, name)
            break

    if not model_path or not model_filename:
        raise HTTPException(status_code=400, detail=f"No supported model artifact found in: {internal_id}")

    return {
        "artifact_dir": artifact_dir,
        "config_path": config_path,
        "model_path": model_path,
        "model_filename": model_filename,
    }


def ensure_directories():
    """Ensure required directories exist."""
    for dir_path in [UPLOADS_DIR, CONTAINERS_DIR, TEMPLATES_DIR]:
        os.makedirs(dir_path, exist_ok=True)


def validate_file_upload(file: UploadFile, allowed_extensions: set, max_size: int) -> None:
    """
    Validate uploaded file for security and size constraints.
    
    Args:
        file: UploadFile object to validate
        allowed_extensions: Set of allowed file extensions
        max_size: Maximum file size in bytes
        
    Raises:
        HTTPException: If validation fails
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File extension {file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {max_size // (1024*1024)}MB"
        )


# Global Docker manager instance
docker_manager: Optional[DockerManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    ensure_directories()
    init_db()  # Initialize SQLite
    global docker_manager
    docker_manager = DockerManager(STORAGE_DIR, DOCKER_DIR)
    
    print("✓ ML Deployment Platform started")
    print(f"✓ Uploads directory: {UPLOADS_DIR}")
    print(f"✓ Containers directory: {CONTAINERS_DIR}")
    print(f"✓ SQLite database initialized")
    
    if docker_manager.is_docker_available():
        print("✓ Docker manager initialized successfully")
    else:
        print("⚠ Docker not available - deployment functionality disabled")
        print("  Please ensure Docker Desktop or Docker Engine is installed and running")
    
    yield
    # Shutdown
    print("✓ Shutting down ML Deployment Platform")


# Create FastAPI app
app = FastAPI(
    title="ML Model Deployment Platform",
    description="Auto-generate Gradio interfaces for ML models with Docker isolation",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/logs")
async def get_logs_root():
    return {"status": "ok"}

@app.get("/containers/{container_id}/logs")
async def get_container_logs(container_id: str, tail: int = 100):
    """
    Fetch logs from a Docker container.
    """
    if not docker_manager:
        return {"logs": "Docker manager not available"}
    
    try:
        # Resolve to real Docker ID if an alias/DB identifier was used
        dep = get_deployment_by_identifier(container_id)
        docker_id = (dep.get("container_id") if dep else container_id) or container_id
        
        if not docker_manager.client:
           return {"logs": []}
            
        container = docker_manager.client.containers.get(docker_id)
        # Fetch logs with timestamps=True to get ISO timestamps for each line
        raw_logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
        
        # Split into list of objects so frontend can map immediately
        formatted_logs = []
        for line in raw_logs.strip().split("\n"):
            if not line:
                continue
            parts = line.split(" ", 1)
            timestamp = parts[0]
            message = parts[1] if len(parts) > 1 else line
            formatted_logs.append({
                "timestamp": timestamp,
                "stream": "stdout",
                "message": message
            })
        
        return {"logs": formatted_logs}
    except Exception as e:
        return {"logs": [{"timestamp": "", "stream": "stderr", "message": f"Logs not available: {str(e)}"}]}

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ML Model Deployment Platform",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    docker_available = docker_manager is not None and docker_manager.is_docker_available()
    return {
        "status": "healthy",
        "docker_available": docker_available,
        "docker_status": "connected" if docker_available else "not_available"
    }


@app.post("/auth/register")
async def register(body: AuthRequest):
    """
    Register a new user account.
    """
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


@app.post("/auth/login")
async def login(body: AuthRequest):
    """
    Login with username and password. Returns a JWT token.
    """
    user = get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_token(user["id"], user["username"])
    return {"status": "success", "token": token, "username": user["username"]}


@app.post("/deploy-model")
async def deploy_model(
    model_file: UploadFile = File(..., description="ML model file (.pkl, .pt, or .onnx)"),
    config_file: UploadFile = File(..., description="Configuration file (config.json)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Deploy an ML model with auto-generated Gradio interface.
    
    Accepts:
    - model_file: Model file (sklearn .pkl, PyTorch .pt, or ONNX .onnx)
    - config_file: JSON configuration file
    
    Returns:
    - status: success/failure
    - container_id: Docker container ID
    - url: Access URL for the deployed model
    """
    temp_dir = None
    
    try:
        # Validate uploaded files
        validate_file_upload(model_file, ALLOWED_MODEL_EXTENSIONS, MAX_FILE_SIZE)
        validate_file_upload(config_file, ALLOWED_CONFIG_EXTENSIONS, MAX_FILE_SIZE)
        
        # Validate file names
        if not config_file.filename or not config_file.filename.endswith('.json'):
            raise HTTPException(
                status_code=400,
                detail="Config file must be a .json file"
            )
        
        if not model_file.filename:
            raise HTTPException(
                status_code=400,
                detail="Model file is required"
            )
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix="ml_deploy_")
        
        # Save uploaded files
        model_path = os.path.join(temp_dir, model_file.filename)
        config_path = os.path.join(temp_dir, "config.json")
        
        # Write model file
        with open(model_path, "wb") as f:
            content = await model_file.read()
            f.write(content)
        
        # Write config file
        with open(config_path, "wb") as f:
            content = await config_file.read()
            f.write(content)
        
        # Read and parse config for validation
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        # Validate configuration
        config = parse_and_validate_config(config_content, model_file.filename)
        
        print(f"✓ Configuration validated for framework: {config['framework']}")
        
        # Generate Gradio application
        app_code = generate_gradio_app(config, model_file.filename)
        app_path = os.path.join(temp_dir, "app.py")
        save_app_to_file(app_code, app_path)
        
        print(f"✓ Gradio app generated: {app_path}")
        
        # Deploy via Docker manager
        if not docker_manager:
            raise HTTPException(status_code=500, detail="Docker manager not initialized")
        
        if not docker_manager.is_docker_available():
            raise HTTPException(
                status_code=503,
                detail="Docker is not available. Please ensure Docker Desktop or Docker Engine is installed and running."
            )
        
        deployment_result = docker_manager.deploy(
            model_path=model_path,
            config_path=config_path,
            app_path=app_path,
            framework=config['framework']
        )
        
        # Save to SQLite
        add_deployment(
            container_id=deployment_result["container_id"],
            internal_id=deployment_result["internal_container_id"],
            model_name=model_file.filename,
            framework=config['framework'],
            task=config['task'],
            host_port=deployment_result["host_port"],
            url=deployment_result["url"]
        )
        
        print(f"✓ Model deployed and saved to database")
        
        return {
            "status": "success",
            "container_id": deployment_result["container_id"],
            "url": deployment_result["url"],
            "framework": config["framework"],
            "task": config["task"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Deployment failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Deployment failed: {str(e)}"
        )
    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/containers", response_model=List[ContainerInfo])
async def list_containers():
    """
    List all active ML model deployments from SQLite, with live port info
    synced from Docker so stale ports are never returned to the frontend.
    """
    try:
        deployments = get_all_deployments()

        # Build a map of short container_id -> live port from Docker.
        # Silently skip if Docker is unavailable – just return DB data as-is.
        live_ports: dict = {}
        if docker_manager and docker_manager.is_docker_available():
            try:
                live_containers = docker_manager.list_containers()
                live_ports = {
                    c["container_id"]: c
                    for c in live_containers
                    if c.get("container_id") and c.get("url")
                }
            except Exception as exc:
                print(f"⚠ Could not fetch live container ports: {exc}")

        for dep in deployments:
            cid = dep.get("container_id")
            if cid and cid in live_ports:
                live = live_ports[cid]
                live_url = live.get("url")
                live_port = None
                if live_url:
                    try:
                        live_port = int(live_url.rsplit(":", 1)[-1])
                    except ValueError:
                        pass
                # Only update when the port actually changed
                if live_port and live_port != dep.get("host_port"):
                    print(f"↻ Updating port for {cid}: {dep.get('host_port')} → {live_port}")
                    dep["host_port"] = live_port
                    dep["url"] = live_url
                    update_deployment_port(cid, live_port, live_url)
            elif cid and cid not in live_ports and dep.get("status") == "running":
                # Container no longer found in Docker – mark stopped in DB
                dep["status"] = "stopped"
                update_status(cid, "stopped")

        return deployments
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch deployments from DB: {str(e)}"
        )


@app.get("/models")
async def list_models(current_user: dict = Depends(get_current_user)):
    """List reusable model artifacts from storage and their deployment status."""
    deployments = get_all_deployments()
    by_internal = {dep.get("internal_id"): dep for dep in deployments if dep.get("internal_id")}

    models = []
    if os.path.isdir(CONTAINERS_DIR):
        for internal_id in sorted(os.listdir(CONTAINERS_DIR)):
            folder = os.path.join(CONTAINERS_DIR, internal_id)
            if not os.path.isdir(folder):
                continue

            model_name = None
            for name in os.listdir(folder):
                if os.path.splitext(name)[1].lower() in ALLOWED_MODEL_EXTENSIONS:
                    model_name = name
                    break

            dep = by_internal.get(internal_id)
            models.append({
                "internal_id": internal_id,
                "model_name": model_name or "unknown",
                "framework": dep.get("framework") if dep else None,
                "task": dep.get("task") if dep else None,
                "status": dep.get("status") if dep else "archived",
                "container_id": dep.get("container_id") if dep else None,
                "url": dep.get("url") if dep else None,
                "host_port": dep.get("host_port") if dep else None,
                "created_at": dep.get("created_at") if dep else None,
            })

    return {"models": models}


@app.post("/models/{internal_id}/deploy")
async def deploy_from_model_artifact(internal_id: str, current_user: dict = Depends(get_current_user)):
    """Create a new deployment from a previously uploaded model artifact folder."""
    if not docker_manager or not docker_manager.is_docker_available():
        raise HTTPException(status_code=503, detail="Docker is not available")

    files = _resolve_artifact_files(internal_id)

    with open(files["config_path"], "r", encoding="utf-8") as f:
        config_content = f.read()

    config = parse_and_validate_config(config_content, files["model_filename"])

    # Re-generate app.py to ensure consistency with current generator logic.
    app_code = generate_gradio_app(config, files["model_filename"])
    temp_dir = tempfile.mkdtemp(prefix="ml_redeploy_")
    try:
        app_path = os.path.join(temp_dir, "app.py")
        save_app_to_file(app_code, app_path)

        deployment_result = docker_manager.deploy(
            model_path=files["model_path"],
            config_path=files["config_path"],
            app_path=app_path,
            framework=config["framework"]
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    add_deployment(
        container_id=deployment_result["container_id"],
        internal_id=deployment_result["internal_container_id"],
        model_name=files["model_filename"],
        framework=config["framework"],
        task=config["task"],
        host_port=deployment_result["host_port"],
        url=deployment_result["url"],
    )

    return {
        "status": "success",
        "container_id": deployment_result["container_id"],
        "internal_id": deployment_result["internal_container_id"],
        "url": deployment_result["url"],
    }


@app.post("/containers/{container_id}/rerun")
async def rerun_container(container_id: str, current_user: dict = Depends(get_current_user)):
    """Rerun a deployment from its preserved artifact folder and update its runtime info."""
    if not docker_manager or not docker_manager.is_docker_available():
        raise HTTPException(status_code=503, detail="Docker is not available")

    dep = get_deployment_by_identifier(container_id)
    if not dep:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {container_id}")

    internal_id = dep.get("internal_id")
    existing_container_id = dep.get("container_id")

    # Best-effort cleanup of an existing runtime before rerun.
    if existing_container_id and dep.get("status") == "running":
        try:
            docker_manager.stop_container(existing_container_id)
        except Exception:
            pass

    files = _resolve_artifact_files(internal_id)
    framework = dep.get("framework")
    if not framework:
        with open(files["config_path"], "r", encoding="utf-8") as f:
            config = parse_and_validate_config(f.read(), files["model_filename"])
            framework = config["framework"]

    deployment_result = docker_manager.rerun_from_artifact(
        internal_id=internal_id,
        framework=framework,
        model_filename=files["model_filename"],
    )

    update_deployment_runtime(
        identifier=container_id,
        container_id=deployment_result["container_id"],
        host_port=deployment_result["host_port"],
        url=deployment_result["url"],
        status="running",
    )

    return {
        "status": "success",
        "container_id": deployment_result["container_id"],
        "internal_id": internal_id,
        "url": deployment_result["url"],
    }


@app.delete("/containers/cleanup-all")
async def cleanup_all_containers(current_user: dict = Depends(get_current_user)):
    """
    Clean up all managed containers and their resources.
    Must be defined BEFORE /containers/{container_id} to avoid route shadowing.
    """
    if not docker_manager:
        raise HTTPException(status_code=500, detail="Docker manager not available")
    
    try:
        docker_manager.cleanup_all_containers()
        remove_all_deployments()
        return {"status": "success", "message": "All containers cleaned up"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup all containers: {str(e)}"
        )


@app.delete("/containers/{container_id}/cleanup")
async def cleanup_container(container_id: str, current_user: dict = Depends(get_current_user)):
    """
    Stop and clean up a container and its resources.
    
    Args:
        container_id: Internal container ID
    """
    if not docker_manager:
        raise HTTPException(status_code=500, detail="Docker manager not available")
    
    try:
        dep = get_deployment_by_identifier(container_id)
        internal_id = dep.get("internal_id") if dep else container_id
        docker_manager.cleanup_container(internal_id)
        remove_deployment_by_identifier(container_id)
        return {"status": "success", "message": f"Container {container_id} cleaned up"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup container: {str(e)}"
        )


@app.delete("/containers/{container_id}")
async def stop_container(container_id: str, current_user: dict = Depends(get_current_user)):
    """
    Stop a running container.
    
    Args:
        container_id: Docker container ID
    """
    if not docker_manager:
        raise HTTPException(status_code=500, detail="Docker manager not available")
    
    try:
        dep = get_deployment_by_identifier(container_id)
        docker_id = dep.get("container_id") if dep else container_id

        docker_manager.stop_container(docker_id)
        update_deployment_runtime(
            identifier=container_id,
            container_id=docker_id,
            host_port=None,
            url=None,
            status="stopped"
        )
        return {"status": "success", "message": f"Container {container_id} stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop container: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)