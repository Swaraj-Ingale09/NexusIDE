"""
Judge system for automatic problem evaluation
Handles test case execution, performance tracking, and result compilation
Supports Python, C, and C++ submissions.
"""

import subprocess
import sys
import os
import time
import json
import tempfile
import shutil
from typing import Dict, List, Tuple, Optional
from django.conf import settings
from django.utils import timezone
from .models import TestCase, ProblemSubmission

# ── Windows-specific subprocess flags ──
_CREATION_FLAGS = 0
if sys.platform == 'win32':
    _CREATION_FLAGS = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

# ── C/C++ compiler paths (MSYS2 on Windows) ──
_MSYS2_UCRT = r'C:\msys64\ucrt64\bin'
_MSYS2_MINGW64 = r'C:\msys64\mingw64\bin'


def _get_work_dir():
    """Return a temp work directory safe for compilation."""
    base = os.environ.get('TEMP', os.environ.get('TMP', tempfile.gettempdir()))
    work_dir = os.path.join(base, 'nexuside_judge')
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def _safe_temp_file(suffix, work_dir=None):
    """Create a temp file in a path without spaces (Windows-safe)."""
    d = work_dir or _get_work_dir()
    fd, path = tempfile.mkstemp(suffix=suffix, dir=d)
    os.close(fd)
    return path


def _detect_c_includes(code):
    """Parse C/C++ code to detect which system headers are used."""
    import re
    includes = set()
    for match in re.finditer(r'#\s*include\s*[<"]([^>"]+)[>"]', code):
        includes.add(match.group(1))
    return includes


def _get_link_flags(includes, lang='c'):
    """Determine linker flags based on detected headers."""
    flags = []
    linked = set()

    if any(h in includes for h in ['math.h', 'cmath']):
        if '-lm' not in linked:
            flags.append('-lm')
            linked.add('-lm')

    if any(h in includes for h in ['pthread.h', 'thread']):
        if '-lpthread' not in linked:
            flags.append('-lpthread')
            linked.add('-lpthread')

    if sys.platform == 'win32':
        if any(h in includes for h in ['winsock2.h', 'ws2tcpip.h', 'windows.h', 'winsock.h']):
            if '-lws2_32' not in linked:
                flags.append('-lws2_32')
                linked.add('-lws2_32')

    if sys.platform != 'win32':
        if any(h in includes for h in ['dlfcn.h']):
            if '-ldl' not in linked:
                flags.append('-ldl')
                linked.add('-ldl')

    if any(h in includes for h in ['openssl/ssl.h', 'openssl/sha.h']):
        if '-lssl' not in linked:
            flags.extend(['-lssl', '-lcrypto'])
            linked.add('-lssl')

    if '-lm' not in linked and lang == 'c':
        flags.append('-lm')

    return flags


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

_compiler_cache = {}


def _find_compiler(candidates):
    """Find a working compiler from a list of candidate names/paths."""
    global _compiler_cache
    cache_key = tuple(candidates)
    if cache_key in _compiler_cache:
        return _compiler_cache[cache_key]

    for compiler in candidates:
        if os.path.isfile(compiler):
            _compiler_cache[cache_key] = compiler
            return compiler

    if sys.platform == 'win32':
        for path in [_MSYS2_UCRT, _MSYS2_MINGW64, r'C:\msys64\usr\bin']:
            for name in candidates:
                full = os.path.join(path, name + ('.exe' if sys.platform == 'win32' else ''))
                if os.path.isfile(full):
                    _compiler_cache[cache_key] = full
                    return full

    for compiler in candidates:
        try:
            result = subprocess.run(
                [compiler, '--version'],
                capture_output=True, timeout=5,
                creationflags=_CREATION_FLAGS,
            )
            if result.returncode == 0:
                _compiler_cache[cache_key] = compiler
                return compiler
        except Exception:
            continue

    if sys.platform == 'win32':
        for name in candidates:
            path = shutil.which(name + '.exe')
            if path:
                _compiler_cache[cache_key] = path
                return path

    _compiler_cache[cache_key] = None
    return None


def _compile_c_code(code, work_dir):
    """Compile C code. Returns (exe_path, error_msg or None)."""
    compiler = _find_compiler(['gcc', 'cc', 'clang'])
    if not compiler:
        return None, 'C compiler not found. Install MinGW-w64 (winget install MSYS2.MSYS2).'

    includes = _detect_c_includes(code)
    is_cpp = bool(includes & _CPP_HEADERS)
    if is_cpp:
        return _compile_cpp_code(code, work_dir)

    link_flags = _get_link_flags(includes, lang='c')
    src_path = _safe_temp_file('.c', work_dir)
    try:
        with open(src_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(code)

        exe_path = src_path.replace('.c', '.exe') if sys.platform == 'win32' else src_path.replace('.c', '')
        compile_cmd = [compiler, '-O2', '-Wall', '-Wextra', src_path, '-o', exe_path]
        compile_cmd.extend(link_flags)

        result = subprocess.run(
            compile_cmd, capture_output=True, text=True, timeout=30,
            encoding='utf-8', errors='replace', creationflags=_CREATION_FLAGS,
        )

        if result.returncode != 0:
            error = result.stderr.replace(src_path, 'code.c')
            if exe_path:
                error = error.replace(exe_path, 'code.exe')
            return None, error.strip()

        return exe_path, None
    except subprocess.TimeoutExpired:
        return None, 'Compilation timed out (30s limit)'
    except Exception as e:
        return None, str(e)


def _compile_cpp_code(code, work_dir):
    """Compile C++ code. Returns (exe_path, error_msg or None)."""
    compiler = _find_compiler(['g++', 'c++', 'clang++'])
    if not compiler:
        return None, 'C++ compiler not found. Install MinGW-w64 (winget install MSYS2.MSYS2).'

    includes = _detect_c_includes(code)
    link_flags = _get_link_flags(includes, lang='cpp')

    src_path = _safe_temp_file('.cpp', work_dir)
    try:
        with open(src_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(code)

        exe_path = src_path.replace('.cpp', '.exe') if sys.platform == 'win32' else src_path.replace('.cpp', '')
        compile_cmd = [compiler, '-O2', '-Wall', '-Wextra', '-std=c++17', src_path, '-o', exe_path]
        compile_cmd.extend(link_flags)

        result = subprocess.run(
            compile_cmd, capture_output=True, text=True, timeout=30,
            encoding='utf-8', errors='replace', creationflags=_CREATION_FLAGS,
        )

        if result.returncode != 0:
            error = result.stderr.replace(src_path, 'code.cpp')
            if exe_path:
                error = error.replace(exe_path, 'code.exe')
            return None, error.strip()

        return exe_path, None
    except subprocess.TimeoutExpired:
        return None, 'Compilation timed out (30s limit)'
    except Exception as e:
        return None, str(e)


def _cleanup_file(path):
    """Safely remove a temp file with retry on Windows."""
    if path and os.path.exists(path):
        for _ in range(3):
            try:
                os.remove(path)
                break
            except PermissionError:
                time.sleep(0.15)
            except Exception:
                break


class JudgeResult:
    """Result of judge execution"""
    def __init__(self):
        self.status = 'pending'
        self.passed_tests = 0
        self.total_tests = 0
        self.execution_time = 0
        self.memory_used = 0
        self.error_message = ''
        self.failed_test_case = None
        self.test_results = []


class CodeJudge:
    """Main judge for evaluating code submissions"""

    def __init__(self, timeout=30, memory_limit=512):
        self.timeout = timeout
        self.memory_limit = memory_limit  # MB

    def judge_submission(self, code: str, test_cases: List[TestCase],
                        language: str = 'python') -> JudgeResult:
        """
        Judge a code submission against all test cases

        Args:
            code: User submitted code
            test_cases: List of TestCase objects
            language: Programming language ('python', 'c', 'cpp')

        Returns:
            JudgeResult with detailed feedback
        """
        result = JudgeResult()
        result.total_tests = len(test_cases)

        language = language.lower().strip()
        if language in ('c', 'cpp', 'c++'):
            result = self._judge_native(code, test_cases, language)
        elif language == 'python':
            result = self._judge_python(code, test_cases)
        else:
            result.status = 'compilation_error'
            result.error_message = f"Language '{language}' not supported. Available: python, c, cpp"
            result.total_tests = len(test_cases)
            return result

        return result

    # ─── Python judge (unchanged logic) ────────────────────────────

    def _judge_python(self, code: str, test_cases: List[TestCase]) -> JudgeResult:
        result = JudgeResult()
        result.total_tests = len(test_cases)

        for idx, test_case in enumerate(test_cases):
            test_result = self._run_python_test_case(code, test_case)
            result.test_results.append(test_result)

            if not test_result['passed']:
                result.failed_test_case = idx
                result.status = test_result['status']
                result.error_message = test_result.get('error', '')
                break

            result.passed_tests += 1
            result.execution_time = max(result.execution_time, test_result['execution_time'])
            result.memory_used = max(result.memory_used, test_result['memory_used'])

        if result.passed_tests == result.total_tests:
            result.status = 'accepted'
        elif result.status == 'pending':
            result.status = 'wrong_answer'

        return result

    def _run_python_test_case(self, code: str, test_case: TestCase) -> Dict:
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, '-u'],
                input=code,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'},
            )
            execution_time = time.time() - start_time

            output = result.stdout.strip()
            expected = test_case.expected_output.strip()
            passed = self._compare_outputs(output, expected)

            if result.returncode != 0 and not passed:
                return {
                    'passed': False,
                    'status': 'runtime_error',
                    'error': result.stderr[:500],
                    'execution_time': execution_time,
                    'memory_used': 0,
                }

            return {
                'passed': passed,
                'status': 'accepted' if passed else 'wrong_answer',
                'output': output,
                'expected': expected,
                'error': result.stderr if result.returncode != 0 else '',
                'execution_time': execution_time,
                'memory_used': 0,
            }

        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'status': 'timeout',
                'error': f'Code execution exceeded {self.timeout} seconds',
                'execution_time': self.timeout,
                'memory_used': 0,
            }
        except Exception as e:
            return {
                'passed': False,
                'status': 'runtime_error',
                'error': str(e)[:500],
                'execution_time': time.time() - start_time,
                'memory_used': 0,
            }

    # ─── C / C++ judge ─────────────────────────────────────────────

    def _judge_native(self, code: str, test_cases: List[TestCase], language: str) -> JudgeResult:
        """Compile once, then run each test case against the compiled binary."""
        result = JudgeResult()
        result.total_tests = len(test_cases)

        work_dir = _get_work_dir()
        exe_path = None

        try:
            # Compile once
            if language == 'python':
                exe_path, compile_err = None, None
            elif language in ('c',):
                exe_path, compile_err = _compile_c_code(code, work_dir)
            else:
                exe_path, compile_err = _compile_cpp_code(code, work_dir)

            if compile_err:
                result.status = 'compilation_error'
                result.error_message = compile_err
                return result

            if exe_path is None:
                result.status = 'compilation_error'
                result.error_message = 'Compilation produced no output'
                return result

            # Run each test case
            for idx, test_case in enumerate(test_cases):
                test_result = self._run_native_test_case(exe_path, test_case)
                result.test_results.append(test_result)

                if not test_result['passed']:
                    result.failed_test_case = idx
                    result.status = test_result['status']
                    result.error_message = test_result.get('error', '')
                    break

                result.passed_tests += 1
                result.execution_time = max(result.execution_time, test_result['execution_time'])
                result.memory_used = max(result.memory_used, test_result['memory_used'])

            if result.passed_tests == result.total_tests:
                result.status = 'accepted'
            elif result.status == 'pending':
                result.status = 'wrong_answer'

        finally:
            # Clean up compiled binary
            if exe_path:
                _cleanup_file(exe_path)
                # Also clean up source file if it exists alongside
                for ext in ['.c', '.cpp']:
                    src = exe_path.replace('.exe', '') + ext if sys.platform == 'win32' else exe_path + ext
                    _cleanup_file(src)

        return result

    def _run_native_test_case(self, exe_path: str, test_case: TestCase) -> Dict:
        """Run a compiled binary with test case input."""
        start_time = time.time()
        try:
            result = subprocess.run(
                [exe_path],
                input=test_case.input_data or '',
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='replace',
                creationflags=_CREATION_FLAGS,
            )
            execution_time = time.time() - start_time

            output = result.stdout.strip()
            expected = test_case.expected_output.strip()
            passed = self._compare_outputs(output, expected)

            if result.returncode != 0 and not passed:
                error_msg = result.stderr[:500] if result.stderr else f'Process exited with code {result.returncode}'
                return {
                    'passed': False,
                    'status': 'runtime_error',
                    'error': error_msg,
                    'execution_time': execution_time,
                    'memory_used': 0,
                }

            return {
                'passed': passed,
                'status': 'accepted' if passed else 'wrong_answer',
                'output': output,
                'expected': expected,
                'error': result.stderr[:500] if result.returncode != 0 else '',
                'execution_time': execution_time,
                'memory_used': 0,
            }

        except subprocess.TimeoutExpired:
            return {
                'passed': False,
                'status': 'timeout',
                'error': f'Code execution exceeded {self.timeout} seconds',
                'execution_time': self.timeout,
                'memory_used': 0,
            }
        except Exception as e:
            return {
                'passed': False,
                'status': 'runtime_error',
                'error': str(e)[:500],
                'execution_time': time.time() - start_time,
                'memory_used': 0,
            }

    # ─── Shared helpers ────────────────────────────────────────────

    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """
        Compare actual output with expected output.
        Handles whitespace variations.
        """
        actual_lines = [line.strip() for line in actual.split('\n') if line.strip()]
        expected_lines = [line.strip() for line in expected.split('\n') if line.strip()]
        return actual_lines == expected_lines


class PerformanceAnalyzer:
    """Analyze code performance metrics"""

    @staticmethod
    def calculate_score(result: JudgeResult, problem_difficulty: int) -> int:
        if result.status == 'accepted':
            base_score = 100
            difficulty_multiplier = (problem_difficulty * 10)
            return min(base_score * difficulty_multiplier, 1000)
        elif result.passed_tests > 0:
            partial_score = (result.passed_tests / result.total_tests) * 50
            difficulty_multiplier = (problem_difficulty * 10)
            return int(partial_score * (difficulty_multiplier / 100))
        else:
            return 0

    @staticmethod
    def get_performance_feedback(result: JudgeResult) -> Dict:
        feedback = {
            'status': result.status,
            'passed_tests': result.passed_tests,
            'total_tests': result.total_tests,
            'execution_time': f"{result.execution_time:.3f}s",
            'memory_used': f"{result.memory_used:.1f}MB",
        }

        status_messages = {
            'accepted': '✓ All test cases passed! Great job!',
            'wrong_answer': f'✗ Wrong answer on test case {result.failed_test_case + 1}',
            'runtime_error': f'✗ Runtime error: {result.error_message[:100]}',
            'timeout': f'✗ Code exceeded time limit ({result.timeout}s)',
            'memory_limit': '✗ Memory limit exceeded',
            'compilation_error': f'✗ {result.error_message}',
        }

        feedback['message'] = status_messages.get(result.status, 'Unknown error')
        return feedback


class LiveJudge:
    """Real-time judge for contests — ACM-ICPC scoring."""

    @staticmethod
    def calculate_contest_score(submissions: List[ProblemSubmission],
                               problem_difficulty: int) -> Tuple[int, int]:
        score = 0
        penalty = 0

        for i, submission in enumerate(submissions):
            if submission.is_accepted:
                score = 100 + (problem_difficulty * 10)
                penalty = (i * 20) + int(submission.execution_time / 60)
                break
            else:
                penalty += 20

        return score, penalty


def evaluate_submission(submission: ProblemSubmission) -> None:
    """
    Main function to evaluate a submission.
    Should be called asynchronously (via Celery in production).
    """
    from .models import UserProblemStats, ProblemAttempt

    judge = CodeJudge(
        timeout=submission.problem.time_limit,
        memory_limit=submission.problem.memory_limit
    )

    test_cases = submission.problem.test_cases.filter(is_hidden=False)

    language = getattr(submission, 'language', 'python') or 'python'
    result = judge.judge_submission(submission.code, list(test_cases), language=language)

    submission.status = result.status
    submission.passed_tests = result.passed_tests
    submission.total_tests = result.total_tests
    submission.execution_time = result.execution_time
    submission.memory_used = result.memory_used
    submission.error_message = result.error_message
    submission.failed_test_case = result.failed_test_case
    submission.judged_at = timezone.now()
    submission.save()

    submission.problem.submissions += 1
    if result.status == 'accepted':
        submission.problem.accepted_submissions += 1
    submission.problem.save()

    stats, _ = UserProblemStats.objects.get_or_create(user=submission.user)
    stats.total_submissions += 1

    if result.status == 'accepted':
        stats.total_accepted += 1

    stats.save()

    attempt, created = ProblemAttempt.objects.get_or_create(
        user=submission.user,
        problem=submission.problem
    )

    attempt.attempts += 1

    if result.status == 'accepted' and not attempt.is_solved:
        attempt.is_solved = True
        attempt.first_solved_at = timezone.now()
        stats.problems_solved += 1
        stats.last_solved = timezone.now()
        stats.save()

    if result.execution_time > 0:
        if not attempt.best_execution_time or result.execution_time < attempt.best_execution_time:
            attempt.best_execution_time = result.execution_time

    attempt.last_attempt_at = timezone.now()
    attempt.save()
