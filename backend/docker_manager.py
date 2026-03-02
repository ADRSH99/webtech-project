"""
Docker Manager Module
Handles container lifecycle: building images, running containers with resource limits,
and cleanup operations. Ensures isolated, secure execution of ML models.
"""

import os
import shutil
import uuid
import logging
import time
import requests as http_requests
from typing import Optional, Dict
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound, ContainerError
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Docker configuration constants
BASE_IMAGE = "python:3.10-slim"
CONTAINER_MEMORY_LIMIT = "512m"
CONTAINER_CPU_LIMIT = 0.5
CONTAINER_PORT = 7860
NETWORK_MODE = "bridge"  # Enable port mapping for Gradio access


class DockerManager:
    """
    Manages Docker operations for ML model deployment.
    Creates isolated containers with resource limits for each model.
    """
    
    def __init__(self, storage_dir: str, docker_dir: str):
        """
        Initialize Docker manager.
        
        Args:
            storage_dir: Directory to store container files (backend/storage)
            docker_dir: Directory containing Dockerfile template (backend/docker)
        """
        self.containers_dir = Path(storage_dir) / "containers"
        self.templates_dir = Path(docker_dir)
        self.client = None
        
        # Ensure containers directory exists
        self.containers_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Docker client
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None
            # Don't raise HTTPException here - let the application handle it gracefully
            logger.warning("Docker not available - deployment functionality will be disabled")
    
    def is_docker_available(self) -> bool:
        """
        Check if Docker is available and connected.
        
        Returns:
            True if Docker is available, False otherwise
        """
        return self.client is not None
    
    def create_container_folder(self) -> str:
        """
        Create a unique folder for container files.
        
        Returns:
            Unique container ID (folder name)
        """
        container_id = str(uuid.uuid4())[:8]
        container_path = self.containers_dir / container_id
        container_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created container folder: {container_path}")
        return container_id
    
    def copy_model_files(
        self, 
        container_id: str, 
        model_path: str, 
        config_path: str,
        app_path: str,
        model_filename: str
    ) -> None:
        """
        Copy model, config, and generated app files to container folder.
        
        Args:
            container_id: Target container ID
            model_path: Path to model file
            config_path: Path to config file
            app_path: Path to generated app.py
            model_filename: Original model filename (preserves extension for correct loading)
        """
        container_path = self.containers_dir / container_id
        
        # Copy files, preserving the original model filename so generated app.py can find it
        shutil.copy2(model_path, container_path / model_filename)
        shutil.copy2(config_path, container_path / "config.json")
        shutil.copy2(app_path, container_path / "app.py")
        
        logger.info(f"Copied model files to container {container_id}")
    
    def create_dockerfile(self, container_id: str, framework: str, model_filename: str) -> str:
        """
        Create Dockerfile from template for specific container.
        
        Args:
            container_id: Target container ID
            framework: ML framework (sklearn, pytorch, onnx)
            model_filename: Original model filename to COPY into the image
        
        Returns:
            Path to created Dockerfile
        """
        container_path = self.containers_dir / container_id
        dockerfile_path = container_path / "Dockerfile"
        
        # Read template
        template_path = self.templates_dir / "Dockerfile.template"
        with open(template_path, 'r') as f:
            template = f.read()
        
        # Determine framework-specific dependencies
        if framework == "sklearn":
            framework_deps = "scikit-learn joblib"
        elif framework == "pytorch":
            framework_deps = "torch torchvision"
        elif framework == "onnx":
            framework_deps = "onnxruntime"
        else:
            framework_deps = ""
        
        # Substitute variables in template
        dockerfile_content = template.format(
            base_image=BASE_IMAGE,
            framework_deps=framework_deps,
            port=CONTAINER_PORT,
            model_filename=model_filename
        )
        
        # Write Dockerfile
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        logger.info(f"Created Dockerfile for container {container_id}")
        return str(dockerfile_path)
    
    def build_image(self, container_id: str) -> str:
        """
        Build Docker image for container.
        
        Args:
            container_id: Container ID to build
        
        Returns:
            Image tag/name
        
        Raises:
            HTTPException: If image build fails
        """
        container_path = self.containers_dir / container_id
        image_tag = f"ml-deploy-{container_id}"
        
        try:
            logger.info(f"Building Docker image: {image_tag}")
            
            # Build image with output logging
            image, build_logs = self.client.images.build(
                path=str(container_path),
                tag=image_tag,
                rm=True,  # Remove intermediate containers
                forcerm=True
            )
            
            # Log build output
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())
            
            logger.info(f"Successfully built image: {image_tag}")
            return image_tag
            
        except DockerException as e:
            logger.error(f"Failed to build Docker image: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to build Docker image: {str(e)}"
            )
    
    def run_container(self, image_tag: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, any]:
        """
        Run Docker container with resource limits.
        
        Args:
            image_tag: Image to run
            labels: Additional labels for the container
        
        Returns:
            Dictionary with container_id and host_port
        
        Raises:
            HTTPException: If container fails to start
        """
        try:
            logger.info(f"Running container from image: {image_tag}")
            
            # Default labels
            container_labels = {
                "ml-deploy": "true",
                "managed-by": "ml-deploy-platform"
            }
            if labels:
                container_labels.update(labels)

            # Run container with security and resource constraints
            container = self.client.containers.run(
                image=image_tag,
                detach=True,  # Run in background
                ports={f'{CONTAINER_PORT}/tcp': None},  # Auto-assign host port
                mem_limit=CONTAINER_MEMORY_LIMIT,
                cpu_quota=int(CONTAINER_CPU_LIMIT * 100000),  # CPU limit in microseconds
                cpu_period=100000,
                network_mode=NETWORK_MODE,  # Enable port mapping for Gradio access
                remove=True,  # Auto-remove on stop
                labels=container_labels
            )
            
            # Get assigned host port
            container.reload()  # Refresh container info
            port_bindings = container.ports
            host_port = None
            
            logger.info(f"Container {container.id[:12]} port bindings: {port_bindings}")
            
            if port_bindings and f'{CONTAINER_PORT}/tcp' in port_bindings:
                port_info = port_bindings[f'{CONTAINER_PORT}/tcp']
                logger.info(f"Port info for {CONTAINER_PORT}/tcp: {port_info}")
                if port_info and len(port_info) > 0:
                    host_port = port_info[0]['HostPort']
            
            if not host_port:
                # Fallback: inspect container to get port
                logger.info("Fallback: Using container inspection to get port")
                container_info = self.client.api.inspect_container(container.id)
                network_settings = container_info['NetworkSettings']
                ports = network_settings.get('Ports', {})
                tcp_port = ports.get(f'{CONTAINER_PORT}/tcp', [])
                logger.info(f"Inspected ports: {ports}")
                logger.info(f"TCP port list: {tcp_port}")
                if tcp_port and len(tcp_port) > 0:
                    host_port = tcp_port[0].get('HostPort')
                    logger.info(f"Found host port: {host_port}")
                else:
                    logger.error(f"No port mapping found for {CONTAINER_PORT}/tcp")
                    logger.error(f"Available ports: {list(ports.keys())}")
            
            if not host_port:
                logger.error(f"Failed to get host port for container {container.id[:12]}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get host port assignment for container"
                )
            
            logger.info(f"Container {container.id[:12]} running on port {host_port}")
            
            return {
                "container_id": container.id,
                "host_port": int(host_port) if host_port else None
            }
            
        except ContainerError as e:
            logger.error(f"Container failed to start: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Container failed to start: {str(e)}"
            )
        except DockerException as e:
            logger.error(f"Failed to run container: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to run container: {str(e)}"
            )
    
    def wait_for_container_ready(self, host_port: int, timeout: int = 90) -> bool:
        """
        Poll the Gradio app until it responds with HTTP 200 or timeout expires.
        
        Args:
            host_port: Host port where the Gradio app is exposed
            timeout: Maximum seconds to wait (default 90 s for pip install inside container)
        
        Returns:
            True if ready before timeout, False otherwise
        """
        url = f"http://localhost:{host_port}"
        deadline = time.time() + timeout
        logger.info(f"Waiting for Gradio app at {url} (timeout={timeout}s)...")
        while time.time() < deadline:
            try:
                resp = http_requests.get(url, timeout=3)
                if resp.status_code == 200:
                    logger.info(f"Gradio app is ready at {url}")
                    return True
            except Exception:
                pass
            time.sleep(3)
        logger.warning(f"Gradio app at {url} did not become ready within {timeout}s")
        return False

    def deploy(
        self, 
        model_path: str, 
        config_path: str, 
        app_path: str,
        framework: str
    ) -> Dict[str, any]:
        """
        Full deployment pipeline: create folder, copy files, build, run.
        
        Args:
            model_path: Path to model file
            config_path: Path to config file
            app_path: Path to generated app.py
            framework: ML framework
        
        Returns:
            Deployment result with container_id and url
        
        Raises:
            HTTPException: If Docker is not available or deployment fails
        """
        if not self.is_docker_available():
            raise HTTPException(
                status_code=503,
                detail="Docker is not available. Please ensure Docker Desktop or Docker Engine is installed and running."
            )
        # Create container folder
        container_id = self.create_container_folder()
        model_filename = Path(model_path).name
        
        try:
            # Copy files, preserving the original model filename
            self.copy_model_files(container_id, model_path, config_path, app_path, model_filename)
            
            # Create Dockerfile referencing the correct model filename
            self.create_dockerfile(container_id, framework, model_filename)
            
            # Build image
            image_tag = self.build_image(container_id)
            
            # Prepare labels for identification
            labels = {
                "ml-deploy": "true",
                "ml-framework": framework
            }
            
            # Run container
            run_result = self.run_container(image_tag, labels=labels)
            
            host_port = run_result["host_port"]
            
            # Wait for Gradio app to be ready before returning the URL
            ready = self.wait_for_container_ready(host_port)
            if not ready:
                logger.warning(f"Container {run_result['container_id'][:12]} started but Gradio may still be initialising")
            
            return {
                "status": "success",
                "container_id": run_result["container_id"][:12],
                "url": f"http://localhost:{host_port}",
                "host_port": host_port,
                "internal_container_id": container_id
            }
            
        except Exception as e:
            # Cleanup on failure
            logger.error(f"Deployment failed for {container_id}: {e}")
            self.cleanup_container(container_id)
            raise
    
    def cleanup_container(self, container_id: str) -> None:
        """
        Clean up container folder and associated resources.
        
        Args:
            container_id: Container ID to clean up
        """
        container_path = self.containers_dir / container_id
        
        try:
            # Stop and remove Docker container if it exists
            if self.client:
                try:
                    # Try to stop and remove container by image tag
                    image_tag = f"ml-deploy-{container_id}"
                    containers = self.client.containers.list(all=True, filters={"ancestor": image_tag})
                    for container in containers:
                        container.stop(timeout=5)
                        container.remove(force=True)
                        logger.info(f"Stopped and removed container {container.id[:12]}")
                    # Remove the built image to free disk space
                    try:
                        self.client.images.remove(image_tag, force=True)
                        logger.info(f"Removed Docker image: {image_tag}")
                    except Exception as img_err:
                        logger.warning(f"Failed to remove image {image_tag}: {img_err}")
                except Exception as e:
                    logger.warning(f"Failed to stop/remove containers for {container_id}: {e}")
            
            # Remove container folder
            if container_path.exists():
                shutil.rmtree(container_path)
                logger.info(f"Cleaned up container folder: {container_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup container {container_id}: {e}")
    
    def cleanup_all_containers(self) -> None:
        """
        Clean up all managed containers and their folders.
        """
        if not self.client:
            logger.warning("Docker client not available for cleanup")
            return
        
        try:
            # Stop and remove all managed containers
            containers = self.client.containers.list(all=True, filters={"label": "ml-deploy=true"})
            for container in containers:
                try:
                    container.stop(timeout=5)
                    container.remove(force=True)
                    logger.info(f"Stopped and removed container {container.id[:12]}")
                except Exception as e:
                    logger.warning(f"Failed to remove container {container.id[:12]}: {e}")
            
            # Remove all ml-deploy images to free disk space
            try:
                images = self.client.images.list(filters={"label": "ml-deploy=true"})
                # Also catch any untagged images starting with the naming convention
                all_images = self.client.images.list()
                for image in all_images:
                    if any(tag.startswith("ml-deploy-") for tag in (image.tags or [])):
                        try:
                            self.client.images.remove(image.id, force=True)
                            logger.info(f"Removed Docker image: {image.tags}")
                        except Exception as img_err:
                            logger.warning(f"Failed to remove image {image.id[:12]}: {img_err}")
            except Exception as e:
                logger.warning(f"Failed to list/remove images: {e}")
            
            # Clean up all container folders
            if self.containers_dir.exists():
                for folder in self.containers_dir.iterdir():
                    if folder.is_dir():
                        try:
                            shutil.rmtree(folder)
                            logger.info(f"Cleaned up container folder: {folder}")
                        except Exception as e:
                            logger.warning(f"Failed to cleanup folder {folder}: {e}")
        except Exception as e:
            logger.error(f"Failed to cleanup all containers: {e}")
    
    def list_containers(self) -> list:
        """
        List all managed containers by querying Docker API.
        
        Returns:
            List of container information dictionaries
        """
        if not self.client:
            return []
        
        try:
            containers = self.client.containers.list(filters={"label": "ml-deploy=true"})
            result = []
            
            for container in containers:
                labels = container.labels
                port_bindings = container.ports
                host_port = None
                
                if port_bindings and f'{CONTAINER_PORT}/tcp' in port_bindings:
                    port_info = port_bindings[f'{CONTAINER_PORT}/tcp']
                    if port_info and len(port_info) > 0:
                        host_port = port_info[0]['HostPort']
                
                result.append({
                    "container_id": container.id[:12],
                    "full_id": container.id,
                    "status": container.status,
                    "url": f"http://localhost:{host_port}" if host_port else None,
                    "framework": labels.get("ml-framework", "unknown")
                })
            
            return result
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            return []

    def stop_container(self, container_id: str) -> None:
        """
        Stop a running container.
        
        Args:
            container_id: Docker container ID
        """
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            logger.info(f"Stopped container: {container_id}")
        except Exception as e:
            logger.warning(f"Failed to stop container {container_id}: {e}")
