"""
Judge system for automatic problem evaluation
Handles test case execution, performance tracking, and result compilation
"""

import subprocess
import sys
import os
import time
import json
from io import StringIO
from typing import Dict, List, Tuple
from django.conf import settings
from django.utils import timezone
from .models import TestCase, ProblemSubmission


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
            language: Programming language
        
        Returns:
            JudgeResult with detailed feedback
        """
        result = JudgeResult()
        result.total_tests = len(test_cases)
        
        if language != 'python':
            result.status = 'compilation_error'
            result.error_message = f"Language {language} not supported. Only Python is available."
            return result
        
        # Run each test case
        for idx, test_case in enumerate(test_cases):
            test_result = self._run_test_case(code, test_case)
            result.test_results.append(test_result)
            
            if not test_result['passed']:
                result.failed_test_case = idx
                result.status = test_result['status']
                result.error_message = test_result.get('error', '')
                break
            
            result.passed_tests += 1
            result.execution_time = max(result.execution_time, test_result['execution_time'])
            result.memory_used = max(result.memory_used, test_result['memory_used'])
        
        # Determine final status
        if result.passed_tests == result.total_tests:
            result.status = 'accepted'
        elif result.status == 'pending':
            result.status = 'wrong_answer'
        
        return result
    
    def _run_test_case(self, code: str, test_case: TestCase) -> Dict:
        """
        Run a single test case against the submitted code
        
        Returns:
            Dict with execution results
        """
        start_time = time.time()
        
        try:
            # Prepare code with input handling
            prepared_code = self._prepare_code(code)
            
            # Run with timeout and input
            result = subprocess.run(
                [sys.executable, '-u'],
                input=prepared_code,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            
            execution_time = time.time() - start_time
            
            # Get output
            output = result.stdout.strip()
            expected = test_case.expected_output.strip()
            
            # Compare outputs
            passed = self._compare_outputs(output, expected)
            
            if result.returncode != 0 and not passed:
                return {
                    'passed': False,
                    'status': 'runtime_error',
                    'error': result.stderr[:500],  # Limit error message
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
                'memory_used': 0,  # Would need psutil to track accurately
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
    
    def _prepare_code(self, code: str) -> str:
        """
        Prepare code for execution by injecting input handling
        This allows stdin-based problems to work
        """
        return code
    
    def _compare_outputs(self, actual: str, expected: str) -> bool:
        """
        Compare actual output with expected output
        Handles whitespace variations
        """
        # Split by lines and strip whitespace
        actual_lines = [line.strip() for line in actual.split('\n') if line.strip()]
        expected_lines = [line.strip() for line in expected.split('\n') if line.strip()]
        
        return actual_lines == expected_lines


class PerformanceAnalyzer:
    """Analyze code performance metrics"""
    
    @staticmethod
    def calculate_score(result: JudgeResult, problem_difficulty: int) -> int:
        """
        Calculate score based on test results and difficulty
        
        Scoring:
        - Accepted: 100 points (scaled by difficulty)
        - Partial: 50 points (scaled by difficulty)
        - Wrong: 0 points
        """
        if result.status == 'accepted':
            # Full points
            base_score = 100
            difficulty_multiplier = (problem_difficulty * 10)  # Easy=10, Medium=20, etc.
            return min(base_score * difficulty_multiplier, 1000)
        
        elif result.passed_tests > 0:
            # Partial credit
            partial_score = (result.passed_tests / result.total_tests) * 50
            difficulty_multiplier = (problem_difficulty * 10)
            return int(partial_score * (difficulty_multiplier / 100))
        
        else:
            return 0
    
    @staticmethod
    def get_performance_feedback(result: JudgeResult) -> Dict:
        """
        Generate user-friendly feedback about performance
        """
        feedback = {
            'status': result.status,
            'passed_tests': result.passed_tests,
            'total_tests': result.total_tests,
            'execution_time': f"{result.execution_time:.3f}s",
            'memory_used': f"{result.memory_used:.1f}MB",
        }
        
        # Status-specific feedback
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
    """
    Real-time judge for contests
    Implements ACM-ICPC scoring (first correct wins, penalties for wrong submissions)
    """
    
    @staticmethod
    def calculate_contest_score(submissions: List[ProblemSubmission], 
                               problem_difficulty: int) -> Tuple[int, int]:
        """
        Calculate contest score and penalty time (ACM-ICPC style)
        
        Returns:
            (score_points, penalty_minutes)
        """
        score = 0
        penalty = 0
        
        for i, submission in enumerate(submissions):
            if submission.is_accepted:
                # Only the first correct submission counts
                score = 100 + (problem_difficulty * 10)
                # Penalty: 20 minutes per wrong submission + time to solve
                penalty = (i * 20) + int(submission.execution_time / 60)
                break
            else:
                # Wrong submission adds penalty
                penalty += 20
        
        return score, penalty


def evaluate_submission(submission: ProblemSubmission) -> None:
    """
    Main function to evaluate a submission
    Should be called asynchronously (via Celery in production)
    """
    from .models import UserProblemStats, ProblemAttempt
    
    # Create judge instance
    judge = CodeJudge(
        timeout=submission.problem.time_limit,
        memory_limit=submission.problem.memory_limit
    )
    
    # Get test cases for this problem
    test_cases = submission.problem.test_cases.filter(is_hidden=False)
    
    # Run judge
    result = judge.judge_submission(submission.code, list(test_cases))
    
    # Update submission
    submission.status = result.status
    submission.passed_tests = result.passed_tests
    submission.total_tests = result.total_tests
    submission.execution_time = result.execution_time
    submission.memory_used = result.memory_used
    submission.error_message = result.error_message
    submission.failed_test_case = result.failed_test_case
    submission.judged_at = timezone.now()
    submission.save()
    
    # Update problem statistics
    submission.problem.submissions += 1
    if result.status == 'accepted':
        submission.problem.accepted_submissions += 1
    submission.problem.save()
    
    # Update user problem stats
    stats, _ = UserProblemStats.objects.get_or_create(user=submission.user)
    stats.total_submissions += 1
    
    if result.status == 'accepted':
        stats.total_accepted += 1
    
    stats.save()
    
    # Update attempt tracking
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
    
    # Track best performance
    if result.execution_time > 0:
        if not attempt.best_execution_time or result.execution_time < attempt.best_execution_time:
            attempt.best_execution_time = result.execution_time
    
    attempt.last_attempt_at = timezone.now()
    attempt.save()
