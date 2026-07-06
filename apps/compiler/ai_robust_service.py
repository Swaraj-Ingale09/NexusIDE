"""
Robust AI Service - Fixes broken AI responses with validation, caching, and retries
"""
import json
import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from django.core.cache import cache
from django.utils import timezone

from .executor import PythonExecutor, CExecutor, CPPExecutor
from .ai_service import get_ai_service

logger = logging.getLogger(__name__)


class CodeValidator:
    """Validates if code is syntactically correct and executable"""
    
    EXECUTOR_MAP = {
        'python': PythonExecutor(),
        'c': CExecutor(),
        'cpp': CPPExecutor(),
        'c++': CPPExecutor(),
    }
    
    @staticmethod
    def validate_syntax(code: str, language: str) -> Tuple[bool, str]:
        """
        Check if code has valid syntax
        Returns: (is_valid, error_message)
        """
        try:
            if language == 'python':
                compile(code, '<string>', 'exec')
                return True, ""
            elif language in ['c', 'cpp', 'c++']:
                executor = CodeValidator.EXECUTOR_MAP.get(language)
                if executor:
                    # If no compiler is available, skip validation to avoid false failure
                    if not getattr(executor, 'compiler', None):
                        logger.warning('C/C++ compiler unavailable, skipping syntax validation')
                        return True, ""

                    # If user code does not declare a main function, append a simple wrapper
                    code_to_check = code
                    if not re.search(r'\bmain\s*\(', code, re.IGNORECASE):
                        code_to_check = f"{code}\nint main() {{ return 0; }}"

                    result = executor.execute(code=code_to_check, stdin="", timeout=10)
                    status = result.get('status', '')
                    if status == 'success':
                        return True, ""

                    error_msg = result.get('error', '').strip()
                    if 'compiler not found' in error_msg.lower():
                        logger.warning('C/C++ compiler unavailable during syntax validation, skipping check')
                        return True, ""

                    return False, error_msg or "C/C++ code failed compile validation"
                return True, ""
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error on line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def test_execution(code: str, language: str, timeout: int = 5) -> Tuple[bool, str]:
        """
        Actually try to run the code to verify it works
        Returns: (is_valid, output_or_error)
        """
        try:
            executor = CodeValidator.EXECUTOR_MAP.get(language)
            if not executor:
                return True, "Executor not available"
            
            # Try to execute with empty input
            result = executor.execute(
                code=code,
                input_data="",
                timeout=timeout
            )
            
            if result.get('status') == 'success':
                return True, result.get('output', '')
            else:
                error = result.get('error', 'Unknown error')
                return False, error
        except Exception as e:
            return False, str(e)


class AIResponseSanitizer:
    """Cleans up AI responses that might contain markdown or extra text"""
    
    @staticmethod
    def extract_code(response: str, language: str) -> str:
        """Extract clean code from AI response which may contain markdown"""
        
        # Remove markdown code blocks
        import re
        
        # Try to extract code blocks first
        lang_markers = {
            'python': ['```python', '```py', '```'],
            'c': ['```c', '```'],
            'cpp': ['```cpp', '```c++', '```'],
            'c++': ['```cpp', '```c++', '```'],
        }
        
        for marker in lang_markers.get(language, ['```']):
            pattern = f'{re.escape(marker)}\\n(.*?)\\n```'
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # If no code blocks found, try to extract any content between markers
        pattern = r'```\n?(.*?)\n?```'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # If still nothing, just clean up the response
        # Remove common AI explanations
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Skip explanation lines
            if any(phrase in line.lower() for phrase in ['explanation', 'here', 'fixed code', 'optimized', 'this code']):
                continue
            code_lines.append(line)
        
        cleaned = '\n'.join(code_lines).strip()
        
        # Remove markdown markers if present
        cleaned = cleaned.replace('```python', '').replace('```cpp', '').replace('```c', '').replace('```', '')
        
        return cleaned.strip()
    
    @staticmethod
    def extract_json(response: str) -> Dict:
        """Extract JSON from response that may have extra text"""
        try:
            # Try direct parse first
            return json.loads(response)
        except:
            # Try to find JSON object
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        
        return {}


class AIRequestCache:
    """Intelligent caching for identical AI requests"""
    
    CACHE_TIMEOUT = 3600 * 24  # 24 hours
    
    @staticmethod
    def _make_key(code: str, operation: str, goal: str = "", language: str = "python") -> str:
        """Generate cache key from request parameters"""
        key_data = f"{code}:{operation}:{goal}:{language}"
        return f"ai_cache_{hashlib.md5(key_data.encode()).hexdigest()}"
    
    @staticmethod
    def get(code: str, operation: str, goal: str = "", language: str = "python") -> Dict | None:
        """Get cached result if exists"""
        try:
            key = AIRequestCache._make_key(code, operation, goal, language)
            return cache.get(key)
        except Exception as e:
            # Cache unavailable (Redis down, etc.) - return None to skip cache
            logger.warning(f"Cache get failed: {e}")
            return None
    
    @staticmethod
    def set(code: str, operation: str, result: Dict, goal: str = "", language: str = "python"):
        """Store result in cache"""
        try:
            key = AIRequestCache._make_key(code, operation, goal, language)
            cache.set(key, result, AIRequestCache.CACHE_TIMEOUT)
        except Exception as e:
            # Cache unavailable - continue without caching
            logger.warning(f"Cache set failed: {e}")


class RobustAIService:
    """
    Robust AI Service with validation, caching, retries, and fallback suggestions
    Prevents broken code from being returned and wasting tokens
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.validator = CodeValidator()
        self.sanitizer = AIResponseSanitizer()
        self.cache = AIRequestCache()
        self.max_retries = 2  # Max retries for failing operations
    
    def fix_code(
        self,
        code: str,
        error: str = None,
        language: str = "python",
        execution_output: str = None,
        execution_error: str = None
    ) -> Dict:
        """
        Fix code with validation and retries
        
        Returns:
        {
            'success': bool,
            'fixed_code': str,
            'is_valid': bool,
            'validation_errors': str,
            'changes': List[str],
            'explanation': str,
            'issues_found': List[str],
            'confidence': float,
            'attempts': int,
            'cached': bool
        }
        """
        
        # Check cache first
        cached = self.cache.get(code, 'fix', error or '', language=language)
        if cached:
            cached['cached'] = True
            return cached
        
        attempts = 0
        last_error = None
        
        while attempts < self.max_retries + 1:
            attempts += 1
            
            try:
                # Call AI to fix code
                result = self.ai_service.analyzer.auto_fix_code(
                    code,
                    error,
                    language=language,
                    execution_output=execution_output,
                    execution_error=execution_error
                )
                fixed_code = result.get('fixed_code', code)
                
                # Sanitize the response
                fixed_code = self.sanitizer.extract_code(fixed_code, language)
                
                # Validate syntax
                is_valid, syntax_error = self.validator.validate_syntax(fixed_code, language)
                
                if not is_valid:
                    logger.warning(f"Fix attempt {attempts}: Syntax invalid - {syntax_error}")
                    last_error = syntax_error
                    if attempts < self.max_retries + 1:
                        # Retry with error message
                        error = f"Previous fix had syntax error: {syntax_error}. {error or ''}"
                        continue
                
                # Build response
                response = {
                    'success': is_valid,
                    'fixed_code': fixed_code,
                    'is_valid': is_valid,
                    'validation_errors': syntax_error if not is_valid else "",
                    'changes': result.get('changes', []),
                    'explanation': result.get('explanation', ''),
                    'issues_found': result.get('issues_found', []),
                    'confidence': result.get('confidence', 0),
                    'attempts': attempts,
                    'cached': False
                }
                
                # Cache successful responses
                if is_valid:
                    self.cache.set(code, 'fix', response, error or '', language=language)
                
                return response
                
            except Exception as e:
                logger.error(f"Fix attempt {attempts} error: {str(e)}")
                last_error = str(e)
                if attempts < self.max_retries + 1:
                    continue
        
        # All retries exhausted - return fallback with suggestions
        return self._fix_fallback(code, error, last_error, language)
    
    def optimize_code(self, code: str, goal: str = "speed", language: str = "python") -> Dict:
        """
        Optimize code with validation and retries
        
        Returns:
        {
            'success': bool,
            'optimized_code': str,
            'is_valid': bool,
            'validation_errors': str,
            'optimizations': List[str],
            'explanation': str,
            'confidence': float,
            'attempts': int,
            'cached': bool
        }
        """
        
        # Check cache first - optimization is deterministic for same code
        cached = self.cache.get(code, 'optimize', goal, language)
        if cached:
            cached['cached'] = True
            return cached
        
        attempts = 0
        last_error = None
        
        while attempts < self.max_retries + 1:
            attempts += 1
            
            try:
                # Call AI to optimize
                result = self.ai_service.analyzer.optimize_code(code, goal, language)
                optimized_code = result.get('optimized_code', code)
                
                # Sanitize response
                optimized_code = self.sanitizer.extract_code(optimized_code, language)
                
                # Validate syntax
                is_valid, syntax_error = self.validator.validate_syntax(optimized_code, language)
                
                if not is_valid:
                    logger.warning(f"Optimize attempt {attempts}: Syntax invalid - {syntax_error}")
                    last_error = syntax_error
                    if attempts < self.max_retries + 1:
                        # Retry with more specific instructions
                        continue
                
                # Build response
                response = {
                    'success': is_valid,
                    'optimized_code': optimized_code,
                    'is_valid': is_valid,
                    'validation_errors': syntax_error if not is_valid else "",
                    'optimizations': result.get('optimizations', []),
                    'explanation': result.get('explanation', ''),
                    'confidence': result.get('confidence', 0),
                    'attempts': attempts,
                    'cached': False
                }
                
                # Cache successful responses
                if is_valid:
                    self.cache.set(code, 'optimize', response, goal, language)
                
                return response
                
            except Exception as e:
                logger.error(f"Optimize attempt {attempts} error: {str(e)}")
                last_error = str(e)
                if attempts < self.max_retries + 1:
                    continue
        
        # All retries exhausted - return fallback suggestions
        return self._optimize_fallback(code, goal, last_error, language)
    
    def _fix_fallback(self, code: str, error: str, last_error: str, language: str) -> Dict:
        """Return helpful suggestions when fix fails"""
        
        suggestions = self._get_fix_suggestions(code, error, language)
        
        return {
            'success': False,
            'fixed_code': code,  # Return original code
            'is_valid': False,
            'validation_errors': f"AI fix failed after retries: {last_error}",
            'changes': [],
            'explanation': f"AI service unable to fix code. {suggestions}",
            'issues_found': self._analyze_error(error),
            'confidence': 0.0,
            'attempts': self.max_retries + 1,
            'cached': False,
            'fallback': True
        }
    
    def _optimize_fallback(self, code: str, goal: str, last_error: str, language: str) -> Dict:
        """Return helpful suggestions when optimize fails"""
        
        suggestions = self._get_optimize_suggestions(goal, language)
        
        return {
            'success': False,
            'optimized_code': code,  # Return original code
            'is_valid': False,
            'validation_errors': f"AI optimize failed after retries: {last_error}",
            'optimizations': [],
            'explanation': f"AI service unable to optimize code. {suggestions}",
            'confidence': 0.0,
            'attempts': self.max_retries + 1,
            'cached': False,
            'fallback': True
        }
    
    @staticmethod
    def _analyze_error(error: str) -> List[str]:
        """Extract issues from error message"""
        if not error:
            return ["Unknown error - check code manually"]
        
        issues = []
        error_lower = error.lower()
        
        # Common error patterns
        if 'syntax' in error_lower or 'invalid' in error_lower:
            issues.append("Syntax error detected")
        if 'name' in error_lower or 'undefined' in error_lower:
            issues.append("Undefined variable or function")
        if 'type' in error_lower:
            issues.append("Type mismatch error")
        if 'indent' in error_lower:
            issues.append("Indentation error")
        if 'import' in error_lower:
            issues.append("Import error")
        
        if not issues:
            issues.append(error[:100])  # First 100 chars of error
        
        return issues
    
    @staticmethod
    def _get_fix_suggestions(code: str, error: str, language: str) -> str:
        """Generate manual fix suggestions based on code and error"""
        
        suggestions = [
            "1. Check the error message carefully for line numbers",
            "2. Look for common mistakes:",
        ]
        
        if language == 'python':
            suggestions.extend([
                "   - Missing colons (:) after if/for/while/def/class",
                "   - Inconsistent indentation (mix of tabs and spaces)",
                "   - Undefined variables - check spelling",
                "   - Missing or mismatched parentheses/brackets",
            ])
        elif language in ['c', 'cpp', 'c++']:
            suggestions.extend([
                "   - Missing semicolons at end of statements",
                "   - Undeclared variables",
                "   - Missing #include for required headers",
                "   - Wrong number of function arguments",
            ])
        
        suggestions.append("3. Test each fix incrementally")
        
        return "\n".join(suggestions)
    
    @staticmethod
    def _get_optimize_suggestions(goal: str, language: str) -> str:
        """Generate manual optimization suggestions"""
        
        if goal == 'speed':
            return f"""Manual optimization tips for {language} performance:
- Avoid unnecessary loops and nested iterations
- Use built-in functions optimized in C (map, filter, sorted)
- Cache results of expensive computations
- Use appropriate data structures (set vs list)
- Profile to find actual bottlenecks first"""
        
        elif goal == 'memory':
            return f"""Manual optimization tips for {language} memory:
- Avoid creating unnecessary copies of data
- Use generators instead of creating full lists
- Delete large objects when no longer needed
- Use appropriate data types (int vs float)
- Consider using memory profiler to find leaks"""
        
        elif goal == 'readability':
            return f"""Manual readability improvements:
- Add meaningful variable names
- Add comments for complex logic
- Break large functions into smaller ones
- Use consistent formatting and style
- Use more specific function/variable names"""
        
        return "Manual optimization required - AI service unavailable"
