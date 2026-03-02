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
    add_user, get_user_by_username
)
from auth import hash_password, verify_password, create_token, get_current_user
from pydantic import BaseModel

# Configuration
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
DOCKER_DIR = os.getenv("DOCKER_DIR", "docker")
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
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
    List all active ML model deployments from SQLite.
    """
    try:
        deployments = get_all_deployments()
        return deployments
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch deployments from DB: {str(e)}"
        )


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
        docker_manager.cleanup_container(container_id)
        remove_deployment(container_id)
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
        docker_manager.stop_container(container_id)
        remove_deployment(container_id)
        return {"status": "success", "message": f"Container {container_id} stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop container: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)