"""
Terminal-style code executor with streaming output and step-by-step execution.
Emulates VS Code terminal functionality with real-time output.
Supports Python, C, and C++ execution.
"""

import subprocess
import sys
import os
import json
import time
import tempfile
import shutil
from io import StringIO
import threading
import queue
from django.conf import settings
from typing import Generator, Dict, Any
import logging

logger = logging.getLogger(__name__)

_CREATION_FLAGS = 0
if sys.platform == 'win32':
    _CREATION_FLAGS = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP


class TerminalExecutor:
    """
    Executes code and streams output line-by-line, similar to VS Code terminal.
    Supports Python, C, and C++ execution.
    """

    def __init__(self, timeout=None):
        self.timeout = timeout or getattr(settings, 'EXECUTION_TIMEOUT', 30)
        self.process = None
        self.output_queue = queue.Queue()
        self.execution_stats = {
            'total_lines': 0,
            'error_lines': 0,
            'input_count': 0,
            'start_time': None,
            'end_time': None,
        }

    def _detect_language(self, code: str) -> str:
        """Auto-detect language from code content."""
        stripped = code.strip()
        if stripped.startswith('#include') or stripped.startswith('#define') or stripped.startswith('#pragma'):
            if 'iostream' in stripped or 'using namespace std' in stripped:
                return 'cpp'
            return 'c'
        if stripped.startswith('import ') or stripped.startswith('from ') or stripped.startswith('def '):
            return 'python'
        return 'python'

    def _find_compiler(self, lang: str):
        """Find compiler for C or C++."""
        compilers = {
            'c': ['gcc', 'cc', 'clang'],
            'cpp': ['g++', 'c++', 'clang++'],
        }
        for compiler in compilers.get(lang, []):
            try:
                result = subprocess.run(
                    [compiler, '--version'],
                    capture_output=True, timeout=5,
                    creationflags=_CREATION_FLAGS,
                )
                if result.returncode == 0:
                    return compiler
            except Exception:
                continue
        # Windows full path lookups
        if sys.platform == 'win32':
            for name in (['gcc.exe', 'cc.exe'] if lang == 'c' else ['g++.exe', 'c++.exe']):
                path = shutil.which(name)
                if path:
                    return path
        return None

    def _get_work_dir(self):
        base = os.environ.get('TEMP', os.environ.get('TMP', tempfile.gettempdir()))
        d = os.path.join(base, 'nexuside_exec')
        os.makedirs(d, exist_ok=True)
        return d

    def execute_streaming(self, code: str, stdin: str = '') -> Generator[Dict[str, Any], None, None]:
        """Execute code and stream output line by line."""
        try:
            self.execution_stats['start_time'] = time.time()

            # Detect language
            lang = self._detect_language(code)
            logger.info("TerminalExecutor: detected language='%s'", lang)

            if lang in ('c', 'cpp'):
                yield from self._execute_native(code, stdin, lang)
            else:
                yield from self._execute_python(code, stdin)

        except Exception as e:
            logger.exception("TerminalExecutor: unhandled exception")
            yield {
                'type': 'error',
                'content': f'Execution error: {str(e)}',
                'line_number': 0,
                'timestamp': time.time(),
                'metadata': {'error_type': 'system'}
            }

    def execute_with_input(self, code: str, input_lines: list = None) -> Generator[Dict[str, Any], None, None]:
        """Execute code with multiple input lines (interactive mode)."""
        try:
            self.execution_stats['start_time'] = time.time()
            input_lines = input_lines or []

            lang = self._detect_language(code)
            logger.info("TerminalExecutor interactive: detected language='%s'", lang)

            if lang in ('c', 'cpp'):
                stdin_data = '\n'.join(input_lines)
                yield from self._execute_native(code, stdin_data, lang)
            else:
                yield from self._execute_python_interactive(code, input_lines)

        except Exception as e:
            logger.exception("TerminalExecutor interactive: unhandled exception")
            yield {
                'type': 'error',
                'content': f'Interactive execution error: {str(e)}',
                'line_number': 0,
                'timestamp': time.time(),
                'metadata': {'error_type': 'system'}
            }

    def _execute_python(self, code: str, stdin: str = '') -> Generator[Dict[str, Any], None, None]:
        """Execute Python code with streaming."""
        injected_code = self._prepare_code(code)

        env = {**os.environ}
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'

        self.process = subprocess.Popen(
            [sys.executable, '-u'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, text=True, encoding='utf-8', errors='replace',
            creationflags=_CREATION_FLAGS,
        )

        yield {
            'type': 'step',
            'content': 'Starting Python execution...',
            'line_number': 0,
            'timestamp': time.time(),
            'metadata': {'status': 'started', 'language': 'python'}
        }

        try:
            stdout_data, stderr_data = self.process.communicate(
                input=injected_code, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            self.process.kill()
            yield {
                'type': 'error',
                'content': f'Execution timeout after {self.timeout} seconds',
                'line_number': 0, 'timestamp': time.time(),
                'metadata': {'error_type': 'timeout'}
            }
            return

        yield from self._yield_output(stdout_data, stderr_data)

    def _execute_python_interactive(self, code: str, input_lines: list) -> Generator[Dict[str, Any], None, None]:
        """Execute Python code interactively."""
        injected_code = self._prepare_code(code)

        env = {**os.environ}
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'

        self.process = subprocess.Popen(
            [sys.executable, '-u'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, text=True, encoding='utf-8', errors='replace', bufsize=1,
            creationflags=_CREATION_FLAGS,
        )

        yield {
            'type': 'step',
            'content': 'Starting interactive Python execution...',
            'line_number': 0,
            'timestamp': time.time(),
            'metadata': {'status': 'started', 'mode': 'interactive', 'language': 'python'}
        }

        input_str = '\n'.join(input_lines)
        try:
            stdout_data, stderr_data = self.process.communicate(
                input=injected_code + '\n' + input_str if input_lines else injected_code,
                timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            self.process.kill()
            yield {
                'type': 'error',
                'content': f'Interactive execution timeout after {self.timeout} seconds',
                'line_number': 0, 'timestamp': time.time(),
                'metadata': {'error_type': 'timeout'}
            }
            return

        yield from self._yield_output(stdout_data, stderr_data)

    def _execute_native(self, code: str, stdin: str, lang: str) -> Generator[Dict[str, Any], None, None]:
        """Execute C or C++ code: compile then run."""
        compiler = self._find_compiler(lang)
        if not compiler:
            yield {
                'type': 'error',
                'content': f'{lang.upper()} compiler not found. Install GCC (MinGW-w64 on Windows) and add to PATH.',
                'line_number': 0, 'timestamp': time.time(),
                'metadata': {'error_type': 'compiler_not_found'}
            }
            return

        work_dir = self._get_work_dir()
        suffix = '.c' if lang == 'c' else '.cpp'
        fd, src_path = tempfile.mkstemp(suffix=suffix, dir=work_dir)
        os.close(fd)
        exe_path = src_path.replace(suffix, '.exe') if sys.platform == 'win32' else src_path.replace(suffix, '')

        try:
            with open(src_path, 'w', encoding='utf-8') as f:
                f.write(code)

            # Compile
            is_msvc = compiler.endswith('cl') or compiler.endswith('cl.exe')
            if is_msvc:
                compile_cmd = [compiler, '/O2', '/W4', src_path, f'/Fe{exe_path}']
                if lang == 'cpp':
                    compile_cmd.insert(3, '/EHsc')
            else:
                std_flag = '-std=c++17' if lang == 'cpp' else None
                compile_cmd = [compiler, '-O2', '-Wall', '-Wextra']
                if std_flag:
                    compile_cmd.append(std_flag)
                compile_cmd.extend([src_path, '-o', exe_path])

            yield {
                'type': 'step',
                'content': f'Compiling {lang.upper()} code...',
                'line_number': 0,
                'timestamp': time.time(),
                'metadata': {'status': 'compiling', 'language': lang, 'compiler': compiler}
            }

            compile_result = subprocess.run(
                compile_cmd, capture_output=True, text=True, timeout=30,
                encoding='utf-8', errors='replace', creationflags=_CREATION_FLAGS,
            )

            if compile_result.returncode != 0:
                error = compile_result.stderr.replace(src_path, f'code{suffix}')
                error = error.replace('\\', '/')
                yield {
                    'type': 'error',
                    'content': f'Compilation Error:\n{error.strip()}',
                    'line_number': 0, 'timestamp': time.time(),
                    'execution_time': time.time() - self.execution_stats['start_time'],
                    'metadata': {'error_type': 'compilation', 'language': lang}
                }
                return

            yield {
                'type': 'step',
                'content': f'Running compiled executable...',
                'line_number': 0,
                'timestamp': time.time(),
                'metadata': {'status': 'running', 'language': lang}
            }

            # Run
            self.process = subprocess.Popen(
                [exe_path],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace',
                creationflags=_CREATION_FLAGS,
            )

            try:
                stdout_data, stderr_data = self.process.communicate(
                    input=stdin, timeout=self.timeout
                )
            except subprocess.TimeoutExpired:
                self.process.kill()
                yield {
                    'type': 'error',
                    'content': f'Execution timeout after {self.timeout} seconds',
                    'line_number': 0, 'timestamp': time.time(),
                    'metadata': {'error_type': 'timeout'}
                }
                return

            yield from self._yield_output(stdout_data, stderr_data)

        except Exception as e:
            yield {
                'type': 'error',
                'content': f'{lang.upper()} execution error: {str(e)}',
                'line_number': 0, 'timestamp': time.time(),
                'metadata': {'error_type': 'system'}
            }
        finally:
            for p in [src_path, exe_path]:
                if p and os.path.exists(p):
                    for attempt in range(3):
                        try:
                            os.remove(p)
                            break
                        except PermissionError:
                            time.sleep(0.1)
                        except Exception:
                            break

    def _yield_output(self, stdout_data: str, stderr_data: str) -> Generator[Dict[str, Any], None, None]:
        """Yield stdout and stderr as line-by-line events."""
        line_num = 0
        if stdout_data:
            for line in stdout_data.splitlines():
                line_num += 1
                self.execution_stats['total_lines'] += 1
                yield {
                    'type': 'output',
                    'content': line,
                    'line_number': line_num,
                    'timestamp': time.time(),
                    'execution_time': time.time() - self.execution_stats['start_time'],
                    'metadata': {}
                }

        if stderr_data:
            for line in stderr_data.splitlines():
                line_num += 1
                self.execution_stats['error_lines'] += 1
                yield {
                    'type': 'error',
                    'content': line,
                    'line_number': line_num,
                    'timestamp': time.time(),
                    'execution_time': time.time() - self.execution_stats['start_time'],
                    'metadata': {'error_type': 'runtime'}
                }

        self.execution_stats['end_time'] = time.time()
        total_time = self.execution_stats['end_time'] - self.execution_stats['start_time']

        yield {
            'type': 'summary',
            'content': f'Process completed in {total_time:.2f}s',
            'line_number': 0,
            'timestamp': time.time(),
            'execution_time': total_time,
            'metadata': {
                'status': 'success' if (self.process and self.process.returncode == 0) else 'error',
                'total_lines': self.execution_stats['total_lines'],
                'error_lines': self.execution_stats['error_lines'],
                'return_code': self.process.returncode if self.process else -1
            }
        }

    def _prepare_code(self, code: str) -> str:
        """Prepare Python code with matplotlib backend injection."""
        return "\n".join([
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
        ])

    def stop(self):
        """Terminate execution."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.warning("Error stopping process: %s", e)
