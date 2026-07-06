"""
Secure Docker-based code execution with resource limits and isolation.
Replaces direct subprocess execution for maximum security.
"""

try:
    import docker
except ImportError:
    docker = None

import subprocess
import json
import logging
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


class DockerExecutor:
    """Base Docker executor with security features"""
    
    # Resource limits for all containers
    RESOURCE_LIMITS = {
        'python': {
            'memory': '256m',      # 256 MB max
            'memswap_limit': '512m',  # Including swap
            'cpu_quota': 100000,   # 0.1 CPU cores (100000 / 100000)
            'cpu_period': 100000,
            'pids_limit': 64,      # Max 64 processes
        },
        'c': {
            'memory': '128m',      # 128 MB max
            'memswap_limit': '256m',
            'cpu_quota': 100000,
            'cpu_period': 100000,
            'pids_limit': 32,
        },
        'cpp': {
            'memory': '128m',
            'memswap_limit': '256m',
            'cpu_quota': 100000,
            'cpu_period': 100000,
            'pids_limit': 32,
        }
    }
    
    TIMEOUT = {
        'python': getattr(settings, 'EXECUTION_TIMEOUT', 30),
        'c': 10,
        'cpp': 10,
    }
    
    def __init__(self, language: str = 'python'):
        self.language = language.lower()
        self.image = f'nexuside-{language}:latest'
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect to Docker daemon"""
        if docker is None:
            raise RuntimeError(
                "Python package 'docker' is not installed. "
                "Install it with: pip install docker "
                "or pip install -r requirements.txt"
            )

        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise RuntimeError(
                "Docker connection failed. Is Docker running? "
                "Run: docker-compose up -d"
            )
    
    def _ensure_image_exists(self) -> bool:
        """Check if sandbox image exists, build if needed"""
        try:
            self.client.images.get(self.image)
            return True
        except docker.errors.ImageNotFound:
            logger.warning(f"Image {self.image} not found. Building...")
            self._build_image()
            return True
        except Exception as e:
            logger.error(f"Error checking image: {e}")
            return False
    
    def _build_image(self):
        """Build the sandbox Docker image"""
        dockerfile_path = Path(__file__).parent / 'dockerfiles'
        dockerfile = dockerfile_path / f'Dockerfile.{self.language}'
        
        if not dockerfile.exists():
            raise FileNotFoundError(f"Dockerfile not found at {dockerfile}")
        
        logger.info(f"Building image {self.image}...")
        try:
            self.client.images.build(
                path=str(dockerfile_path),
                dockerfile=dockerfile.name,
                tag=self.image,
                rm=True,
            )
            logger.info(f"Successfully built {self.image}")
        except Exception as e:
            logger.error(f"Failed to build image: {e}")
            raise
    
    def execute(self, code: str, stdin: str = '', timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute code in isolated Docker container.
        
        Args:
            code: Source code to execute
            stdin: Standard input
            timeout: Execution timeout in seconds
        
        Returns:
            {
                'output': str,
                'error': str,
                'status': 'success|error|timeout',
                'execution_time': float,
                'memory_used': float (MB),
                'return_code': int,
                'artifacts': list,
            }
        """
        if not self._ensure_image_exists():
            return self._error_response("Failed to ensure sandbox image")
        
        timeout = timeout or self.TIMEOUT.get(self.language, 30)
        start_time = time.time()
        container = None
        
        try:
            # Prepare code file
            code_file = self._prepare_code_file(code)
            
            # Get resource limits
            limits = self.RESOURCE_LIMITS.get(self.language, {})
            
            # Run container
            container = self.client.containers.run(
                self.image,
                command=self._get_command(),
                stdout=True,
                stderr=True,
                detach=True,
                mem_limit=limits.get('memory'),
                memswap_limit=limits.get('memswap_limit'),
                cpu_quota=limits.get('cpu_quota'),
                cpu_period=limits.get('cpu_period'),
                pids_limit=limits.get('pids_limit'),
                read_only=True,  # Read-only root filesystem
                tmpfs={'/tmp': 'size=50m'},  # Writable temp directory
                network_disabled=True,  # No network access
                volumes_from=None,  # No volume mounts
                working_dir='/sandbox',
                environment=['PYTHONUNBUFFERED=1', 'MPLCONFIGDIR=/tmp/matplotlib'],
            )
            
            # Wait for completion with timeout
            try:
                exit_code = container.wait(timeout=timeout)['StatusCode']
            except docker.errors.APIError:
                # Timeout exceeded
                container.kill()
                execution_time = time.time() - start_time
                return {
                    'output': '',
                    'error': f'Execution timeout (>{timeout}s)',
                    'status': 'timeout',
                    'execution_time': execution_time,
                    'memory_used': 0,
                    'return_code': -1,
                    'artifacts': [],
                }
            
            # Get output
            output = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            error = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            
            # Get stats (memory usage)
            memory_used = 0
            try:
                stats = container.stats(stream=False)
                if stats and 'memory_stats' in stats and 'usage' in stats['memory_stats']:
                    memory_used = stats['memory_stats']['usage'] / 1024 / 1024  # Convert to MB
            except Exception as e:
                logger.warning(f"Failed to get memory stats: {e}")
            
            execution_time = time.time() - start_time
            
            return {
                'output': output,
                'error': error.strip(),
                'status': 'success' if exit_code == 0 else 'error',
                'execution_time': execution_time,
                'memory_used': round(memory_used, 2),
                'return_code': exit_code,
                'artifacts': [],
            }
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Docker execution error: {e}")
            return {
                'output': '',
                'error': str(e),
                'status': 'error',
                'execution_time': execution_time,
                'memory_used': 0,
                'return_code': -1,
                'artifacts': [],
            }
        
        finally:
            # Cleanup container
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")
    
    def _prepare_code_file(self, code: str) -> str:
        """Write code to temporary file in container"""
        # This will be handled by volume mounting in the run command
        return code
    
    def _get_command(self) -> str:
        """Get execution command for the language"""
        raise NotImplementedError
    
    def _error_response(self, error: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            'output': '',
            'error': error,
            'status': 'error',
            'execution_time': 0,
            'memory_used': 0,
            'return_code': -1,
            'artifacts': [],
        }


class DockerPythonExecutor(DockerExecutor):
    """Execute Python code in Docker sandbox"""
    
    def __init__(self):
        super().__init__('python')
    
    def execute(self, code: str, stdin: str = '', timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute Python code with Docker isolation"""
        timeout = timeout or self.TIMEOUT.get(self.language, 30)
        start_time = time.time()
        container = None
        
        try:
            if not self._ensure_image_exists():
                return self._error_response("Failed to ensure sandbox image")
            
            limits = self.RESOURCE_LIMITS.get(self.language, {})
            
            # Prepare injected code with matplotlib support
            injected_code = self._prepare_python_code(code)
            
            # Create container and execute
            container = self.client.containers.run(
                self.image,
                command=['python', '-u', '-c', injected_code],
                stdout=True,
                stderr=True,
                detach=True,
                mem_limit=limits.get('memory'),
                memswap_limit=limits.get('memswap_limit'),
                cpu_quota=limits.get('cpu_quota'),
                cpu_period=limits.get('cpu_period'),
                pids_limit=limits.get('pids_limit'),
                read_only=True,
                tmpfs={'/tmp': 'size=100m', '/dev/shm': 'size=100m'},
                network_disabled=True,
                working_dir='/sandbox',
                environment=['PYTHONUNBUFFERED=1', 'MPLCONFIGDIR=/tmp/matplotlib'],
                user='runner',  # Run as non-root
            )
            
            # Wait with timeout
            try:
                exit_code = container.wait(timeout=timeout)['StatusCode']
            except docker.errors.APIError:
                container.kill()
                execution_time = time.time() - start_time
                return {
                    'output': '',
                    'error': f'Execution timeout (>{timeout}s)',
                    'status': 'timeout',
                    'execution_time': execution_time,
                    'memory_used': 0,
                    'return_code': -1,
                    'artifacts': [],
                }
            
            # Collect output
            output = container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
            error = container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
            
            # Extract figures from output
            artifacts = self._extract_artifacts(output)
            output = self._remove_artifact_markers(output)
            
            # Memory stats (with fallback if unavailable)
            memory_used = 0
            try:
                stats = container.stats(stream=False)
                if stats and 'memory_stats' in stats and 'usage' in stats['memory_stats']:
                    memory_used = stats['memory_stats']['usage'] / 1024 / 1024
            except Exception as e:
                logger.warning(f"Failed to get memory stats: {e}")
            
            execution_time = time.time() - start_time
            
            return {
                'output': output,
                'error': error.strip(),
                'status': 'success' if exit_code == 0 else 'error',
                'execution_time': execution_time,
                'memory_used': round(memory_used, 2),
                'return_code': exit_code,
                'artifacts': artifacts,
            }
        
        except Exception as e:
            logger.error(f"Python Docker execution error: {e}")
            return self._error_response(str(e))
        
        finally:
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
    
    def _prepare_python_code(self, code: str) -> str:
        """Inject matplotlib backend, figure capture, and file handling"""
        return "\n".join([
            "import os",
            "import glob",
            "os.chdir('/tmp')",  # Change to writable directory
            "import matplotlib",
            "matplotlib.use('Agg')",
            "import matplotlib.pyplot as plt",
            "_NEXUSIDE_FIGS = []",
            "_orig_show = plt.show",
            "def _nexuside_show(*args, **kwargs):",
            "    try:",
            "        fig = plt.gcf()",
            "        buf = __import__('io').BytesIO()",
            "        fig.savefig(buf, format='png', bbox_inches='tight')",
            "        _NEXUSIDE_FIGS.append('data:image/png;base64,' + __import__('base64').b64encode(buf.getvalue()).decode('ascii'))",
            "    except Exception:",
            "        pass",
            "    return _orig_show(*args, **kwargs)",
            "plt.show = _nexuside_show",
            code,
            "print('__NEXUSIDE_FIGURES__' + str(len(_NEXUSIDE_FIGS)))",
            "for _img in _NEXUSIDE_FIGS: print(_img)",
            "import glob as _glob",
            "print('__NEXUSIDE_FILES__')",
            "for _f in _glob.glob('/tmp/*.csv') + _glob.glob('/tmp/*.txt') + _glob.glob('/tmp/*.json'):",
            "    try:",
            "        with open(_f, 'rb') as _file:",
            "            _name = __import__('os').path.basename(_f)",
            "            _ext = _f.split('.')[-1]",
            "            _data = __import__('base64').b64encode(_file.read()).decode('ascii')",
            "            print(f'__FILE__:{_ext}:{_name}:{_data}')",
            "    except: pass",
        ])
    
    def _extract_artifacts(self, output: str) -> list:
        """Extract base64 figures and files from output and format as expected by frontend"""
        artifacts = []
        lines = output.split('\n')
        
        capturing_figs = False
        for line in lines:
            if '__NEXUSIDE_FIGURES__' in line:
                try:
                    count = int(line.split('__NEXUSIDE_FIGURES__')[1])
                    capturing_figs = count > 0
                except:
                    pass
            elif '__NEXUSIDE_FILES__' in line:
                capturing_figs = False
            elif capturing_figs and line.startswith('data:image'):
                # Format image artifact
                artifacts.append({
                    'type': 'image',
                    'data': line.strip()
                })
            elif line.startswith('__FILE__:'):
                # Format file artifact: __FILE__:ext:filename:base64_data
                try:
                    parts = line.split(':', 3)
                    if len(parts) == 4:
                        ext = parts[1]
                        filename = parts[2]
                        data = parts[3]
                        artifacts.append({
                            'type': 'file',
                            'ext': ext,
                            'name': filename,
                            'data': data
                        })
                except:
                    pass
        
        return artifacts
    
    def _remove_artifact_markers(self, output: str) -> str:
        """Remove artifact markers from output"""
        lines = [
            line for line in output.split('\n')
            if '__NEXUSIDE_FIGURES__' not in line 
            and '__NEXUSIDE_FILES__' not in line
            and not line.startswith('data:image')
            and not line.startswith('__FILE__:')
        ]
        return '\n'.join(lines).strip()
    
    def _get_command(self) -> str:
        return 'python'


class DockerCExecutor(DockerExecutor):
    """Execute C code in Docker sandbox"""
    
    def __init__(self):
        super().__init__('c')
    
    def _get_command(self) -> str:
        return 'gcc'


class DockerCPPExecutor(DockerExecutor):
    """Execute C++ code in Docker sandbox"""
    
    def __init__(self):
        super().__init__('cpp')
    
    def _get_command(self) -> str:
        return 'g++'


# Backward compatibility: Check if Docker is available, fall back to subprocess
def get_executor(language: str):
    """Get appropriate executor (Docker or subprocess fallback)"""
    language = language.lower()
    
    try:
        # Try Docker first
        if language == 'python':
            return DockerPythonExecutor()
        elif language in ['c', 'c_language']:
            return DockerCExecutor()
        elif language in ['cpp', 'c++']:
            return DockerCPPExecutor()
    except Exception as e:
        logger.warning(f"Docker executor failed for {language}: {e}")
        logger.warning("Falling back to subprocess execution (UNSAFE!)")
        
        # Fallback to subprocess (import old executors)
        from apps.compiler.executor import PythonExecutor, CExecutor, CPPExecutor
        
        if language == 'python':
            return PythonExecutor()
        elif language in ['c', 'c_language']:
            return CExecutor()
        elif language in ['cpp', 'c++']:
            return CPPExecutor()
    
    raise ValueError(f"Unsupported language: {language}")
