<<<<<<< HEAD
"""
Main FastAPI Application
Entry point for the ML model deployment platform.
Handles file uploads, orchestrates validation, app generation, and deployment.
"""

import os
import tempfile
import shutil
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import modules
from config_validator import parse_and_validate_config
from app_generator import generate_gradio_app, save_app_to_file
from docker_manager import DockerManager

# Configuration
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
DOCKER_DIR = os.getenv("DOCKER_DIR", "docker")
UPLOADS_DIR = os.path.join(STORAGE_DIR, "uploads")
CONTAINERS_DIR = os.path.join(STORAGE_DIR, "containers")
TEMPLATES_DIR = DOCKER_DIR
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024  # 100MB default
ALLOWED_MODEL_EXTENSIONS = {".pkl", ".pt", ".pth", ".onnx"}
ALLOWED_CONFIG_EXTENSIONS = {".json"}
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")


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
    global docker_manager
    docker_manager = DockerManager(STORAGE_DIR, DOCKER_DIR)
    
    print("✓ ML Deployment Platform started")
    print(f"✓ Uploads directory: {UPLOADS_DIR}")
    print(f"✓ Containers directory: {CONTAINERS_DIR}")
    
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


@app.post("/deploy-model")
async def deploy_model(
    model_file: UploadFile = File(..., description="ML model file (.pkl, .pt, or .onnx)"),
    config_file: UploadFile = File(..., description="Configuration file (config.json)")
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
        
        print(f"✓ Model deployed successfully")
        print(f"  Container ID: {deployment_result['container_id']}")
        print(f"  URL: {deployment_result['url']}")
        
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


@app.delete("/containers/cleanup-all")
async def cleanup_all_containers():
    """
    Clean up all managed containers and their resources.
    Must be defined BEFORE /containers/{container_id} to avoid route shadowing.
    """
    if not docker_manager:
        raise HTTPException(status_code=500, detail="Docker manager not available")
    
    try:
        docker_manager.cleanup_all_containers()
        return {"status": "success", "message": "All containers cleaned up"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup all containers: {str(e)}"
        )


@app.delete("/containers/{container_id}/cleanup")
async def cleanup_container(container_id: str):
    """
    Stop and clean up a container and its resources.
    
    Args:
        container_id: Internal container ID
    """
    if not docker_manager:
        raise HTTPException(status_code=500, detail="Docker manager not available")
    
    try:
        docker_manager.cleanup_container(container_id)
        return {"status": "success", "message": f"Container {container_id} cleaned up"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup container: {str(e)}"
        )


@app.delete("/containers/{container_id}")
async def stop_container(container_id: str):
    """
    Stop a running container.
    
    Args:
        container_id: Docker container ID
    """
    if not docker_manager:
        raise HTTPException(status_code=500, detail="Docker manager not available")
    
    try:
        docker_manager.stop_container(container_id)
        return {"status": "success", "message": f"Container {container_id} stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop container: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)