"""
NexusIDE Code Executor — handles Python, C, C++, and SQL execution.
Supports complex code with all libraries, proper stdin, large output,
linked libraries for C/C++, and in-memory SQLite for SQL.
"""

import subprocess
import sys
import os
import shutil
from django.conf import settings
import json
import time
import tempfile
import logging
import re
import threading
import base64
import glob as _glob
import sqlite3

logger = logging.getLogger(__name__)

# ── Windows-specific subprocess flags ──
_CREATION_FLAGS = 0
if sys.platform == 'win32':
    _CREATION_FLAGS = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

# ── C/C++ compiler paths (MSYS2 on Windows) ──
_C_COMPILER = None
_CPP_COMPILER = None
_COMPILER_DETECTED = False

# Default include/lib paths for MSYS2 on Windows
_MSYS2_UCRT = r'C:\msys64\ucrt64\bin'
_MSYS2_MINGW64 = r'C:\msys64\mingw64\bin'


def _get_work_dir():
    """Return a temp work directory safe for compilation."""
    base = os.environ.get('TEMP', os.environ.get('TMP', tempfile.gettempdir()))
    work_dir = os.path.join(base, 'nexuside_exec')
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def _safe_temp_file(suffix, work_dir=None):
    """Create a temp file in a path without spaces (Windows-safe)."""
    d = work_dir or _get_work_dir()
    fd, path = tempfile.mkstemp(suffix=suffix, dir=d)
    os.close(fd)
    return path


# File extensions to capture as artifacts
_CAPTURE_EXTENSIONS = {'.txt', '.csv', '.json', '.xml', '.html', '.htm', '.md', '.log', '.dat', '.pdf', '.xlsx', '.xls'}


def _capture_created_files(work_dir, before_files):
    """Scan work_dir for new files created during execution, return as base64 artifacts.

    Args:
        work_dir: directory to scan
        before_files: set of filenames that existed before execution
    Returns:
        list of artifact dicts with type='file', name, ext, data (base64)
    """
    artifacts = []
    if not work_dir or not os.path.isdir(work_dir):
        return artifacts

    try:
        current_files = set(os.listdir(work_dir))
        new_files = current_files - before_files

        for fname in new_files:
            fpath = os.path.join(work_dir, fname)
            if not os.path.isfile(fpath):
                continue
            _, ext = os.path.splitext(fname)
            if ext.lower() not in _CAPTURE_EXTENSIONS:
                continue
            try:
                with open(fpath, 'rb') as f:
                    raw = f.read()
                if len(raw) > 5 * 1024 * 1024:  # skip files > 5MB
                    logger.warning("_capture_created_files: skipping %s (%d bytes)", fname, len(raw))
                    continue
                b64 = base64.b64encode(raw).decode('ascii')
                artifacts.append({
                    'type': 'file',
                    'name': fname,
                    'ext': ext.lstrip('.'),
                    'data': b64,
                })
                logger.info("_capture_created_files: captured %s (%d bytes)", fname, len(raw))
            except Exception as e:
                logger.warning("_capture_created_files: failed to read %s: %s", fname, e)
    except Exception as e:
        logger.warning("_capture_created_files: scan failed: %s", e)

    return artifacts


def _detect_c_includes(code):
    """Parse C/C++ code to detect which system headers are used."""
    includes = set()
    for match in re.finditer(r'#\s*include\s*[<"]([^>"]+)[>"]', code):
        includes.add(match.group(1))
    return includes


def _get_link_flags(includes, lang='c'):
    """Determine linker flags based on detected headers."""
    flags = []
    linked = set()

    # Math library
    if any(h in includes for h in ['math.h', 'cmath']):
        if '-lm' not in linked:
            flags.append('-lm')
            linked.add('-lm')

    # Threading
    if any(h in includes for h in ['pthread.h', 'thread']):
        if '-lpthread' not in linked:
            flags.append('-lpthread')
            linked.add('-lpthread')

    # Windows sockets
    if sys.platform == 'win32':
        if any(h in includes for h in ['winsock2.h', 'ws2tcpip.h', 'windows.h', 'winsock.h']):
            if '-lws2_32' not in linked:
                flags.append('-lws2_32')
                linked.add('-lws2_32')

    # Dynamic loading (dlopen, etc.)
    if sys.platform != 'win32':
        if any(h in includes for h in ['dlfcn.h']):
            if '-ldl' not in linked:
                flags.append('-ldl')
                linked.add('-ldl')

    # OpenSSL
    if any(h in includes for h in ['openssl/ssl.h', 'openssl/sha.h']):
        if '-lssl' not in linked:
            flags.extend(['-lssl', '-lcrypto'])
            linked.add('-lssl')

    # Default: always link math for C (harmless for C++)
    if '-lm' not in linked and lang == 'c':
        flags.append('-lm')

    return flags


# ══════════════════════════════════════════════════════════════════════
# Python Executor
# ══════════════════════════════════════════════════════════════════════

# Matplotlib injection code (prepended to every Python execution)
MATPLOTLIB_INJECTION = r'''
import warnings as _nexus_warnings
_nexus_warnings.filterwarnings("ignore")
import sys as _nexus_sys
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as _nexus_plt
    import matplotlib.animation as _nexus_anim
    import io as _nexus_io, base64 as _nexus_b64

    _NEXUSIDE_FIGS = []
    _NEXUSIDE_ANIM = None

    def _nexuside_artistlist_clear(self):
        _to_rm = [a for a in self._axes._children if self._type_check(a)]
        for _a in _to_rm:
            self._axes._children.remove(_a)
    try:
        _al_cls = type(_nexus_plt.figure().gca().collections)
        if not hasattr(_al_cls, 'clear'):
            _al_cls.clear = _nexuside_artistlist_clear
        _nexus_plt.close('all')
    except Exception:
        pass

    class _NexusIDE_FuncAnimation(_nexus_anim.FuncAnimation):
        def __init__(self, *a, **kw):
            global _NEXUSIDE_ANIM
            with _nexus_warnings.catch_warnings():
                _nexus_warnings.simplefilter("ignore")
                super().__init__(*a, **kw)
            _NEXUSIDE_ANIM = self

    _nexus_anim.FuncAnimation = _NexusIDE_FuncAnimation
    matplotlib.animation.FuncAnimation = _NexusIDE_FuncAnimation

    _orig_show = _nexus_plt.show
    def _nexuside_show(*a, **kw):
        global _NEXUSIDE_ANIM
        _handled = False
        try:
            if _NEXUSIDE_ANIM is not None:
                ani = _NEXUSIDE_ANIM
                _NEXUSIDE_ANIM = None
                fig = ani._fig
                func = ani._func
                sc = getattr(ani, "_save_count", None) or 50
                step = max(1, sc // 10)
                for idx in range(0, sc, step):
                    try:
                        func(idx)
                        try:
                            fig.canvas.draw()
                        except Exception:
                            pass
                        buf = _nexus_io.BytesIO()
                        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
                        _NEXUSIDE_FIGS.append("data:image/png;base64," + _nexus_b64.b64encode(buf.getvalue()).decode())
                        buf.close()
                    except Exception as _frame_err:
                        print("[NexusIDE] animation frame %d error: %s" % (idx, _frame_err), file=_nexus_sys.stderr)
                _handled = True
            else:
                fig = _nexus_plt.gcf()
                if fig.get_axes():
                    try:
                        fig.canvas.draw()
                    except Exception:
                        pass
                    buf = _nexus_io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches="tight")
                    _NEXUSIDE_FIGS.append("data:image/png;base64," + _nexus_b64.b64encode(buf.getvalue()).decode())
                    _handled = True
        except Exception as _show_err:
            print("[NexusIDE] matplotlib show error: %s" % _show_err, file=_nexus_sys.stderr)
        _nexus_plt.close("all")
        if _handled:
            return None
        return _orig_show(*a, **kw)
    _nexus_plt.show = _nexuside_show
    _NEXUSIDE_MATPLOTLIB_OK = True
except Exception:
    _NEXUSIDE_MATPLOTLIB_OK = False
    _NEXUSIDE_FIGS = []
'''


class PythonExecutor:
    """Execute Python code with matplotlib support, large output handling, and robust timeout."""

    def __init__(self, timeout=None):
        self.timeout = timeout or getattr(settings, 'EXECUTION_TIMEOUT', 30)

    def execute(self, code, stdin='', timeout=None):
        work_dir = None
        try:
            effective_timeout = timeout or self.timeout
            start_time = time.time()

            if isinstance(code, bytes):
                code = code.decode('utf-8', errors='replace')
            if isinstance(stdin, bytes):
                stdin = stdin.decode('utf-8', errors='replace')

            # Create a dedicated working directory for this execution
            work_dir = _get_work_dir()
            before_files = set(os.listdir(work_dir))

            parts = [MATPLOTLIB_INJECTION, "", code, "", r"""
if "_NEXUSIDE_FIGS" in dir() and _NEXUSIDE_FIGS:
    print("__NEXUSIDE_FIGURES__" + str(len(_NEXUSIDE_FIGS)))
    for _img in _NEXUSIDE_FIGS:
        print(_img)
"""]
            full_code = "\n".join(parts)

            env = {**os.environ}
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUNBUFFERED'] = '1'

            logger.info("PythonExecutor: running code (%d chars), timeout=%ds", len(code), effective_timeout)

            result = subprocess.run(
                [sys.executable, '-u', '-c', full_code],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=env,
                cwd=work_dir,
                encoding='utf-8',
                errors='replace',
                creationflags=_CREATION_FLAGS,
            )

            execution_time = time.time() - start_time

            # Parse matplotlib artifacts from stdout
            output_text = result.stdout
            artifacts = []
            figures_prefix = '__NEXUSIDE_FIGURES__'
            if figures_prefix in output_text:
                lines = output_text.splitlines()
                parsed = []
                out_lines = []
                for line in lines:
                    if line.startswith(figures_prefix):
                        continue
                    if line.startswith('data:image/png;base64,'):
                        parsed.append({'type': 'image', 'mime': 'image/png', 'data': line})
                        continue
                    out_lines.append(line)
                artifacts = parsed
                output_text = '\n'.join(out_lines).strip()

            # Capture files created during execution (txt, csv, json, etc.)
            file_artifacts = _capture_created_files(work_dir, before_files)
            artifacts.extend(file_artifacts)

            # Clean up captured files from work_dir
            for fa in file_artifacts:
                fpath = os.path.join(work_dir, fa['name'])
                try:
                    if os.path.exists(fpath):
                        os.remove(fpath)
                except Exception:
                    pass

            # Filter harmless warnings from stderr
            suppress = [
                'FigureCanvasAgg is non-interactive',
                'cache_frame_data',
                'Animation was deleted without rendering',
                'UserWarning',
                'DeprecationWarning',
            ]
            filtered = [
                l.strip() for l in (result.stderr or '').splitlines()
                if l.strip() and not any(w in l for w in suppress)
            ]
            error_value = '\n'.join(filtered).strip()

            # Determine status
            if result.returncode != 0 and error_value:
                status = 'error'
            elif result.returncode != 0:
                status = 'error'
                error_value = error_value or 'Process exited with non-zero return code'
            else:
                status = 'success'

            logger.info("PythonExecutor: done in %.2fs, return_code=%d, output_len=%d",
                        execution_time, result.returncode, len(output_text))

            return {
                'output': output_text,
                'error': error_value,
                'status': status,
                'execution_time': execution_time,
                'return_code': result.returncode,
                'artifacts': artifacts,
            }

        except subprocess.TimeoutExpired:
            logger.warning("PythonExecutor: timeout after %ds", effective_timeout)
            return {
                'output': '',
                'error': f'Execution timeout after {effective_timeout} seconds',
                'status': 'timeout',
                'execution_time': effective_timeout,
                'return_code': -1,
                'artifacts': [],
            }
        except Exception as e:
            logger.exception("PythonExecutor: exception")
            return {
                'output': '',
                'error': str(e),
                'status': 'error',
                'execution_time': 0,
                'return_code': -1,
                'artifacts': [],
            }


# ══════════════════════════════════════════════════════════════════════
# C Executor
# ══════════════════════════════════════════════════════════════════════

class CExecutor:
    """Execute C code with auto-linking, complex code support, and Windows compatibility."""

    _compiler_cache = None

    def __init__(self, timeout=None):
        self.timeout = timeout or getattr(settings, 'EXECUTION_TIMEOUT', 30)
        self.compiler = self._find_compiler()

    def _find_compiler(self):
        if CExecutor._compiler_cache is not None:
            return CExecutor._compiler_cache

        # Direct path lookup first (fastest)
        candidates = ['gcc', 'cc', 'clang']

        # On Windows, check common install locations
        if sys.platform == 'win32':
            for path in [_MSYS2_UCRT, _MSYS2_MINGW64, r'C:\msys64\usr\bin']:
                gcc = os.path.join(path, 'gcc.exe')
                if os.path.isfile(gcc):
                    CExecutor._compiler_cache = gcc
                    logger.info("CExecutor: found compiler at '%s'", gcc)
                    return gcc

        for compiler in candidates:
            try:
                result = subprocess.run(
                    [compiler, '--version'],
                    capture_output=True, timeout=5,
                    creationflags=_CREATION_FLAGS,
                )
                if result.returncode == 0:
                    CExecutor._compiler_cache = compiler
                    logger.info("CExecutor: found compiler '%s'", compiler)
                    return compiler
            except Exception:
                continue

        # Windows: try shutil.which
        if sys.platform == 'win32':
            for name in ['gcc.exe', 'cc.exe']:
                path = shutil.which(name)
                if path:
                    CExecutor._compiler_cache = path
                    logger.info("CExecutor: found compiler via which: '%s'", path)
                    return path

        CExecutor._compiler_cache = None
        logger.warning("CExecutor: no C compiler found")
        return None

    _CPP_HEADERS = {
        'iostream', 'fstream', 'sstream', 'string', 'vector', 'map', 'set',
        'algorithm', 'memory', 'functional', 'utility', 'tuple', 'array',
        'list', 'deque', 'queue', 'stack', 'unordered_map', 'unordered_set',
        'numeric', 'iterator', 'type_traits', 'cassert', 'cstdlib', 'cstring',
        'cmath', 'climits', 'cfloat', 'exception', 'stdexcept', 'bitset',
        'regex', 'chrono', 'thread', 'mutex', 'atomic', 'condition_variable',
        'future', 'complex', 'valarray', 'initializer_list', 'variant',
        'optional', 'any', 'format', 'ranges', 'concepts', 'span',
    }

    def execute(self, code, stdin='', timeout=None):
        if not self.compiler:
            return {
                'output': '',
                'error': (
                    'C compiler not found.\n'
                    'Install MinGW-w64 and add to PATH:\n'
                    '  winget install MSYS2.MSYS2\n'
                    '  Then: pacman -S mingw-w64-ucrt-x86_64-gcc\n'
                    '  Or download from: https://www.mingw-w64.org/'
                ),
                'status': 'error',
                'execution_time': 0,
                'return_code': -1,
                'artifacts': [],
            }

        src_path = None
        exe_path = None
        try:
            if isinstance(code, bytes):
                code = code.decode('utf-8', errors='replace')
            if isinstance(stdin, bytes):
                stdin = stdin.decode('utf-8', errors='replace')

            start_time = time.time()
            work_dir = _get_work_dir()
            before_files = set(os.listdir(work_dir))

            # Detect includes for auto-linking
            includes = _detect_c_includes(code)

            # Auto-detect C++ and switch compiler
            is_cpp = bool(includes & self._CPP_HEADERS)
            if is_cpp:
                if CPPExecutor._compiler_cache:
                    cpp_compiler = CPPExecutor._compiler_cache
                else:
                    cpp_compiler = CPPExecutor()._find_compiler()
                if cpp_compiler:
                    logger.info("CExecutor: detected C++ headers, switching to g++: %s", cpp_compiler)
                    compiler = cpp_compiler
                    lang = 'cpp'
                else:
                    compiler = self.compiler
                    lang = 'c'
                    logger.warning("CExecutor: C++ detected but g++ not found, falling back to gcc")
            else:
                compiler = self.compiler
                lang = 'c'

            link_flags = _get_link_flags(includes, lang=lang)
            logger.info("CExecutor: detected includes=%s, link_flags=%s, lang=%s", includes, link_flags, lang)

            # Create temp files in a safe directory
            src_suffix = '.cpp' if is_cpp else '.c'
            src_path = _safe_temp_file(src_suffix, work_dir)
            with open(src_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(code)

            exe_path = src_path.replace(src_suffix, '.exe') if sys.platform == 'win32' else src_path.replace(src_suffix, '')

            # Build compile command
            is_msvc = 'cl' in os.path.basename(compiler).lower()

            if is_msvc:
                compile_cmd = [compiler, '/O2', '/W4', src_path, f'/Fe{exe_path}']
            else:
                compile_cmd = [compiler, '-O2', '-Wall', '-Wextra', src_path, '-o', exe_path]
                compile_cmd.extend(link_flags)

            logger.info("CExecutor: compile cmd=%s", compile_cmd)

            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace',
                creationflags=_CREATION_FLAGS,
            )

            if compile_result.returncode != 0:
                error_msg = self._parse_compile_error(compile_result.stderr, src_path)
                exec_time = time.time() - start_time
                logger.warning("CExecutor: compile failed in %.2fs: %s", exec_time, error_msg[:300])
                return {
                    'output': '',
                    'error': f"Compilation Error:\n{error_msg}",
                    'status': 'error',
                    'execution_time': exec_time,
                    'return_code': compile_result.returncode,
                    'artifacts': [],
                }

            compile_time = time.time() - start_time
            logger.info("CExecutor: compiled in %.2fs", compile_time)

            # Execute with stdin
            run_result = subprocess.run(
                [exe_path],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                encoding='utf-8',
                errors='replace',
                creationflags=_CREATION_FLAGS,
            )

            execution_time = time.time() - start_time
            output = run_result.stdout
            error = run_result.stderr.strip() if run_result.stderr else ''

            status = 'error' if run_result.returncode != 0 else 'success'
            # If there's stderr but no stdout and returncode is 0, still report stderr as info
            if run_result.returncode == 0 and error and not output:
                output = error
                error = ''

            # Capture files created during execution
            artifacts = _capture_created_files(work_dir, before_files)
            for fa in artifacts:
                fpath = os.path.join(work_dir, fa['name'])
                try:
                    if os.path.exists(fpath):
                        os.remove(fpath)
                except Exception:
                    pass

            logger.info("CExecutor: done in %.2fs, return_code=%d, out=%d, err=%d",
                        execution_time, run_result.returncode, len(output), len(error))

            return {
                'output': output,
                'error': error,
                'status': status,
                'execution_time': execution_time,
                'return_code': run_result.returncode,
                'artifacts': artifacts,
            }

        except subprocess.TimeoutExpired:
            logger.warning("CExecutor: timeout after %ds", timeout or self.timeout)
            return {
                'output': '',
                'error': f'Execution timeout after {timeout or self.timeout} seconds\n'
                         'The program may be waiting for stdin input, running an infinite loop,\n'
                         'or performing heavy computation.',
                'status': 'timeout',
                'execution_time': timeout or self.timeout,
                'return_code': -1,
                'artifacts': [],
            }
        except Exception as e:
            logger.exception("CExecutor: exception")
            return {
                'output': '',
                'error': f'Execution Error: {str(e)}',
                'status': 'error',
                'execution_time': 0,
                'return_code': -1,
                'artifacts': [],
            }
        finally:
            self._cleanup(src_path, exe_path)

    def _parse_compile_error(self, stderr, src_path):
        error = stderr.replace(src_path, 'code.c')
        if exe_path := src_path.replace('.c', '.exe'):
            error = error.replace(exe_path, 'code.exe')
        error = error.replace('\\', '/')
        return error.strip()

    def _cleanup(self, src_path, exe_path):
        for path in [src_path, exe_path]:
            if path and os.path.exists(path):
                for _ in range(3):
                    try:
                        os.remove(path)
                        break
                    except PermissionError:
                        time.sleep(0.15)
                    except Exception:
                        break


# ══════════════════════════════════════════════════════════════════════
# C++ Executor
# ══════════════════════════════════════════════════════════════════════

class CPPExecutor:
    """Execute C++ code with auto-linking, complex code support, and Windows compatibility."""

    _compiler_cache = None

    def __init__(self, timeout=None):
        self.timeout = timeout or getattr(settings, 'EXECUTION_TIMEOUT', 30)
        self.compiler = self._find_compiler()

    def _find_compiler(self):
        if CPPExecutor._compiler_cache is not None:
            return CPPExecutor._compiler_cache

        candidates = ['g++', 'c++', 'clang++']

        if sys.platform == 'win32':
            for path in [_MSYS2_UCRT, _MSYS2_MINGW64, r'C:\msys64\usr\bin']:
                gpp = os.path.join(path, 'g++.exe')
                if os.path.isfile(gpp):
                    CPPExecutor._compiler_cache = gpp
                    logger.info("CPPExecutor: found compiler at '%s'", gpp)
                    return gpp

        for compiler in candidates:
            try:
                result = subprocess.run(
                    [compiler, '--version'],
                    capture_output=True, timeout=5,
                    creationflags=_CREATION_FLAGS,
                )
                if result.returncode == 0:
                    CPPExecutor._compiler_cache = compiler
                    logger.info("CPPExecutor: found compiler '%s'", compiler)
                    return compiler
            except Exception:
                continue

        if sys.platform == 'win32':
            for name in ['g++.exe', 'c++.exe', 'clang++.exe']:
                path = shutil.which(name)
                if path:
                    CPPExecutor._compiler_cache = path
                    return path

        CPPExecutor._compiler_cache = None
        logger.warning("CPPExecutor: no C++ compiler found")
        return None

    def execute(self, code, stdin='', timeout=None):
        if not self.compiler:
            return {
                'output': '',
                'error': (
                    'C++ compiler not found.\n'
                    'Install MinGW-w64 and add to PATH:\n'
                    '  winget install MSYS2.MSYS2\n'
                    '  Then: pacman -S mingw-w64-ucrt-x86_64-gcc\n'
                    '  Or download from: https://www.mingw-w64.org/'
                ),
                'status': 'error',
                'execution_time': 0,
                'return_code': -1,
                'artifacts': [],
            }

        src_path = None
        exe_path = None
        try:
            if isinstance(code, bytes):
                code = code.decode('utf-8', errors='replace')
            if isinstance(stdin, bytes):
                stdin = stdin.decode('utf-8', errors='replace')

            start_time = time.time()
            work_dir = _get_work_dir()
            before_files = set(os.listdir(work_dir))

            includes = _detect_c_includes(code)
            link_flags = _get_link_flags(includes, lang='cpp')
            logger.info("CPPExecutor: includes=%s, link_flags=%s", includes, link_flags)

            src_path = _safe_temp_file('.cpp', work_dir)
            with open(src_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(code)

            exe_path = src_path.replace('.cpp', '.exe') if sys.platform == 'win32' else src_path.replace('.cpp', '')

            compiler = self.compiler
            is_msvc = 'cl' in os.path.basename(compiler).lower()

            if is_msvc:
                compile_cmd = [compiler, '/O2', '/W4', '/EHsc', '/std:c++17', src_path, f'/Fe{exe_path}']
            else:
                compile_cmd = [compiler, '-O2', '-Wall', '-Wextra', '-std=c++17', src_path, '-o', exe_path]
                compile_cmd.extend(link_flags)

            logger.info("CPPExecutor: compile cmd=%s", compile_cmd)

            compile_result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace',
                creationflags=_CREATION_FLAGS,
            )

            if compile_result.returncode != 0:
                error_msg = self._parse_compile_error(compile_result.stderr, src_path)
                exec_time = time.time() - start_time
                logger.warning("CPPExecutor: compile failed in %.2fs: %s", exec_time, error_msg[:300])
                return {
                    'output': '',
                    'error': f"Compilation Error:\n{error_msg}",
                    'status': 'error',
                    'execution_time': exec_time,
                    'return_code': compile_result.returncode,
                    'artifacts': [],
                }

            compile_time = time.time() - start_time
            logger.info("CPPExecutor: compiled in %.2fs", compile_time)

            run_result = subprocess.run(
                [exe_path],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                encoding='utf-8',
                errors='replace',
                creationflags=_CREATION_FLAGS,
            )

            execution_time = time.time() - start_time
            output = run_result.stdout
            error = run_result.stderr.strip() if run_result.stderr else ''

            status = 'error' if run_result.returncode != 0 else 'success'
            if run_result.returncode == 0 and error and not output:
                output = error
                error = ''

            # Capture files created during execution
            artifacts = _capture_created_files(work_dir, before_files)
            for fa in artifacts:
                fpath = os.path.join(work_dir, fa['name'])
                try:
                    if os.path.exists(fpath):
                        os.remove(fpath)
                except Exception:
                    pass

            logger.info("CPPExecutor: done in %.2fs, return_code=%d", execution_time, run_result.returncode)

            return {
                'output': output,
                'error': error,
                'status': status,
                'execution_time': execution_time,
                'return_code': run_result.returncode,
                'artifacts': artifacts,
            }

        except subprocess.TimeoutExpired:
            logger.warning("CPPExecutor: timeout after %ds", timeout or self.timeout)
            return {
                'output': '',
                'error': f'Execution timeout after {timeout or self.timeout} seconds\n'
                         'The program may be waiting for stdin input, running an infinite loop,\n'
                         'or performing heavy computation.',
                'status': 'timeout',
                'execution_time': timeout or self.timeout,
                'return_code': -1,
                'artifacts': [],
            }
        except Exception as e:
            logger.exception("CPPExecutor: exception")
            return {
                'output': '',
                'error': f'Execution Error: {str(e)}',
                'status': 'error',
                'execution_time': 0,
                'return_code': -1,
                'artifacts': [],
            }
        finally:
            self._cleanup(src_path, exe_path)

    def _parse_compile_error(self, stderr, src_path):
        error = stderr.replace(src_path, 'code.cpp')
        if exe_path := src_path.replace('.cpp', '.exe'):
            error = error.replace(exe_path, 'code.exe')
        error = error.replace('\\', '/')
        return error.strip()

    def _cleanup(self, src_path, exe_path):
        for path in [src_path, exe_path]:
            if path and os.path.exists(path):
                for _ in range(3):
                    try:
                        os.remove(path)
                        break
                    except PermissionError:
                        time.sleep(0.15)
                    except Exception:
                        break


# ══════════════════════════════════════════════════════════════════════
# SQL Executor
# ══════════════════════════════════════════════════════════════════════

class SQLExecutor:
    """Execute SQL queries against a persistent in-memory SQLite database.
    
    The database persists across executions within the same process, so
    CREATE TABLE, INSERT, UPDATE etc. carry over between runs.
    """

    _conn = None  # class-level persistent connection
    _seeded = False

    def __init__(self, timeout=5):
        self.timeout = timeout

    @classmethod
    def _get_conn(cls):
        if cls._conn is None:
            cls._conn = sqlite3.connect(':memory:', check_same_thread=False)
            cls._conn.row_factory = sqlite3.Row
            cls._conn.execute("PRAGMA journal_mode=WAL")
        return cls._conn

    @classmethod
    def reset(cls):
        """Drop all tables and re-seed the database."""
        if cls._conn:
            cls._conn.close()
            cls._conn = None
        cls._seeded = False

    def execute(self, code, stdin=''):
        start_time = time.time()
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if not SQLExecutor._seeded:
                self._seed(cursor)
                conn.commit()
                SQLExecutor._seeded = True

            statements = [s.strip() for s in code.split(';') if s.strip()]
            last_select_result = None
            rows_affected = 0

            for statement in statements:
                cursor.execute(statement)
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = [list(row) for row in cursor.fetchall()]
                    last_select_result = {
                        "type": "table",
                        "columns": columns,
                        "rows": rows,
                        "affected_rows": len(rows)
                    }
                else:
                    rows_affected += cursor.rowcount if cursor.rowcount != -1 else 0

            conn.commit()
            execution_time = time.time() - start_time

            if last_select_result:
                output_str = json.dumps(last_select_result)
            else:
                code_upper = code.upper().strip()
                is_ddl = code_upper.startswith(('CREATE ', 'ALTER ', 'DROP '))
                verb = 'created' if code_upper.startswith('CREATE ') else 'altered' if code_upper.startswith('ALTER ') else 'dropped' if code_upper.startswith('DROP ') else 'executed'
                if is_ddl:
                    msg = f"Query executed successfully. {verb.title()} successfully."
                else:
                    msg = f"Query executed successfully. {rows_affected} row{'s' if rows_affected != 1 else ''} affected."
                output_str = json.dumps({
                    "type": "message",
                    "message": msg,
                })

            return {
                'output': output_str,
                'error': '',
                'status': 'success',
                'execution_time': execution_time,
                'return_code': 0,
                'artifacts': [],
            }
        except sqlite3.Error as e:
            return {
                'output': '',
                'error': f"SQL Error: {str(e)}",
                'status': 'error',
                'execution_time': time.time() - start_time,
                'return_code': 1,
                'artifacts': [],
            }

    @classmethod
    def get_schema(cls):
        """Return current database schema as a dict of table info."""
        conn = cls._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {}
        for (table_name,) in cursor.fetchall():
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for col in cursor.fetchall():
                columns.append({
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default': col[4],
                    'pk': bool(col[5]),
                })
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            tables[table_name] = {
                'columns': columns,
                'row_count': row_count,
            }
        return tables

    def _seed(self, cursor):
        cursor.execute('''
            CREATE TABLE Customers (
                CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                CustomerName TEXT,
                ContactName TEXT,
                City TEXT,
                Country TEXT
            )
        ''')
        cursor.executemany('''
            INSERT INTO Customers (CustomerName, ContactName, City, Country)
            VALUES (?, ?, ?, ?)
        ''', [
            ('Alfreds Futterkiste', 'Maria Anders', 'Berlin', 'Germany'),
            ('Ana Trujillo Emparedados', 'Ana Trujillo', 'México D.F.', 'Mexico'),
            ('Antonio Moreno Taquería', 'Antonio Moreno', 'México D.F.', 'Mexico'),
            ('Around the Horn', 'Thomas Hardy', 'London', 'UK'),
            ('Berglunds snabbköp', 'Christina Berglund', 'Luleå', 'Sweden'),
            ('Blauer See Delikatessen', 'Hanna Moos', 'Mannheim', 'Germany'),
            ('Blondel père et fils', 'Frédérique Citeaux', 'Strasbourg', 'France'),
            ('Bólido Comidas preparadas', 'Martín Sommer', 'Madrid', 'Spain'),
            ('Bon app\'', 'Laurence Lebihan', 'Marseille', 'France'),
            ('Bottom-Dollar Markets', 'Elizabeth Lincoln', 'Tsawwassen', 'Canada'),
        ])

        cursor.execute('''
            CREATE TABLE Products (
                ProductID INTEGER PRIMARY KEY AUTOINCREMENT,
                ProductName TEXT,
                Price REAL,
                Unit TEXT
            )
        ''')
        cursor.executemany('''
            INSERT INTO Products (ProductName, Price, Unit)
            VALUES (?, ?, ?)
        ''', [
            ('Chais', 18.00, '10 boxes x 20 bags'),
            ('Chang', 19.00, '24 - 12 oz bottles'),
            ('Aniseed Syrup', 10.00, '12 - 550 ml bottles'),
            ('Chef Anton\'s Cajun Seasoning', 22.00, '48 - 6 oz jars'),
            ('Chef Anton\'s Gumbo Mix', 21.35, '36 boxes'),
            ('Grandma\'s Boysenberry Spread', 25.00, '12 - 8 oz jars'),
            ('Uncle Bob\'s Organic Dried Pears', 30.00, '12 - 1 lb pkgs.'),
            ('Northwoods Cranberry Sauce', 40.00, '12 - 12 oz jars'),
            ('Mishi Kobe Niku', 97.00, '50 - 300 g pkgs.'),
            ('Ikura', 31.00, '12 - 200 ml jars'),
        ])

        cursor.execute('''
            CREATE TABLE Orders (
                OrderID INTEGER PRIMARY KEY AUTOINCREMENT,
                CustomerID INTEGER,
                ProductID INTEGER,
                Quantity INTEGER,
                OrderDate TEXT,
                FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
                FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
            )
        ''')
        cursor.executemany('''
            INSERT INTO Orders (CustomerID, ProductID, Quantity, OrderDate)
            VALUES (?, ?, ?, ?)
        ''', [
            (1, 1, 10, '2024-01-15'),
            (1, 3, 5, '2024-02-10'),
            (2, 2, 3, '2024-01-20'),
            (3, 5, 1, '2024-03-05'),
            (4, 7, 12, '2024-02-28'),
            (5, 1, 8, '2024-01-22'),
            (6, 4, 6, '2024-03-15'),
            (7, 9, 2, '2024-02-14'),
            (8, 10, 4, '2024-03-01'),
            (9, 6, 3, '2024-01-30'),
        ])


# ══════════════════════════════════════════════════════════════════════
# Router
# ══════════════════════════════════════════════════════════════════════

def execute_code(code, language='python', stdin='', timeout=None):
    """
    Execute code in Python, C, C++, or SQL.
    Returns: dict with output, error, status, execution_time, return_code, artifacts
    """
    language = language.lower().strip()

    if language == 'python':
        return PythonExecutor(timeout).execute(code, stdin)

    elif language in ['c', 'c_language']:
        return CExecutor(timeout).execute(code, stdin)

    elif language in ['cpp', 'c++']:
        return CPPExecutor(timeout).execute(code, stdin)

    elif language == 'sql':
        return SQLExecutor(timeout).execute(code, stdin)

    else:
        return {
            'output': '',
            'error': f'Unsupported language: {language}. Supported: python, c, cpp, sql',
            'status': 'error',
            'execution_time': 0,
            'return_code': -1,
            'artifacts': [],
        }


def execute_python_code(code, timeout=None):
    """Backward compatible wrapper for Python execution."""
    return execute_code(code, 'python', timeout=timeout)
