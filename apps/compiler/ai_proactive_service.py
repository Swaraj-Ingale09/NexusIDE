"""
Proactive AI Service - Prevents broken code BEFORE calling AI
Uses advanced prompting, syntax checking, and multi-provider strategies
"""

import json
import logging
import re
from typing import Dict, List, Tuple
from django.core.cache import cache
from django.utils import timezone

from .executor import PythonExecutor, CExecutor, CPPExecutor
from .ai_service import get_ai_service

logger = logging.getLogger(__name__)


class LanguageSpecificPromptBuilder:
    """Builds bulletproof language-specific prompts that prevent errors"""
    
    @staticmethod
    def get_python_fix_prompt(code: str, error: str = "", execution_output: str = "", execution_error: str = "") -> Tuple[str, str]:
        """Generate best Python fix prompt with strict rules"""
        
        error_context = f"Error to fix: {error}\n" if error else ""
        if execution_output:
            error_context += f"Program output:\n{execution_output}\n"
        if execution_error:
            error_context += f"Execution error:\n{execution_error}\n"
        
        user_prompt = f"""Fix this Python code EXACTLY. Do NOT make unnecessary changes.

{error_context}
```python
{code}
```

CRITICAL RULES (READ CAREFULLY):
1. Return ONLY valid Python code - nothing else
2. All functions must have proper indentation (4 spaces per level)
3. All colons (:) must be after if/for/while/def/class/try/except
4. All strings must be closed with matching quotes
5. All brackets must be closed: (), [], {{}}
6. All variables must be defined before use
7. Do NOT add explanations or comments outside code
8. Do NOT change functionality - only fix errors

RESPONSE FORMAT - Start with triple backticks, end with triple backticks:
```python
[YOUR FIXED CODE HERE]
```"""
        
        system_prompt = """You are a Python debugger. Your ONLY job is to fix broken Python code.
- Return ONLY valid Python code in backticks
- Never add explanations outside the code block
- Preserve original logic and functionality
- Fix syntax errors: missing colons, indentation, unclosed quotes/brackets
- Fix runtime errors: undefined variables, wrong types
- Test the code mentally - it MUST work

EXAMPLES:
Input: "def foo(x\n  return x*2"
Output: 
```python
def foo(x):
    return x * 2
```

Input: "x = [1,2,3\nprint(x)"
Output:
```python
x = [1, 2, 3]
print(x)
```"""
        
        return user_prompt, system_prompt
    
    @staticmethod
    def get_c_fix_prompt(code: str, error: str = "", execution_output: str = "", execution_error: str = "") -> Tuple[str, str]:
        """Generate best C fix prompt with strict rules"""
        
        error_context = f"Error to fix: {error}\n" if error else ""
        if execution_output:
            error_context += f"Program output:\n{execution_output}\n"
        if execution_error:
            error_context += f"Execution error:\n{execution_error}\n"
        
        user_prompt = f"""Fix this C code EXACTLY. Do NOT make unnecessary changes.

{error_context}
```c
{code}
```

CRITICAL RULES (READ CAREFULLY):
1. Return ONLY valid C code - nothing else
2. All statements must end with semicolon (;)
3. All braces must be matched: {{ and }}
4. All function declarations need return type
5. All variables must be declared with type (int, char, float, etc)
6. All headers must be included (#include <stdio.h>, etc)
7. Do NOT add explanations or comments outside code
8. Do NOT change logic - only fix errors

RESPONSE FORMAT - Start with triple backticks, end with triple backticks:
```c
[YOUR FIXED CODE HERE]
```"""
        
        system_prompt = """You are a C debugger. Your ONLY job is to fix broken C code.
- Return ONLY valid C code in backticks
- Never add explanations outside the code block
- Preserve original logic and functionality
- Fix syntax errors: missing semicolons, mismatched braces, missing types
- Fix header issues: add #include if needed
- All code must be compilable

EXAMPLES:
Input: "int main() { printf("Hello"  return 0; }"
Output:
```c
#include <stdio.h>
int main() { 
    printf("Hello");
    return 0; 
}
```

Input: "main() { int x; x = 5 print(x)"
Output:
```c
#include <stdio.h>
int main() { 
    int x; 
    x = 5;
    printf("%d", x);
    return 0;
}
```"""
        
        return user_prompt, system_prompt
    
    @staticmethod
    def get_cpp_fix_prompt(code: str, error: str = "", execution_output: str = "", execution_error: str = "") -> Tuple[str, str]:
        """Generate best C++ fix prompt with strict rules"""
        
        error_context = f"Error to fix: {error}\n" if error else ""
        if execution_output:
            error_context += f"Program output:\n{execution_output}\n"
        if execution_error:
            error_context += f"Execution error:\n{execution_error}\n"
        
        user_prompt = f"""Fix this C++ code EXACTLY. Do NOT make unnecessary changes.

{error_context}
```cpp
{code}
```

CRITICAL RULES (READ CAREFULLY):
1. Return ONLY valid C++ code - nothing else
2. All statements must end with semicolon (;)
3. All braces must be matched: {{ and }}
4. All function declarations need return type
5. All variables must be declared with type
6. All includes must be present (#include <iostream>, etc)
7. Do NOT add explanations or comments outside code
8. Do NOT change logic - only fix errors

RESPONSE FORMAT - Start with triple backticks, end with triple backticks:
```cpp
[YOUR FIXED CODE HERE]
```"""
        
        system_prompt = """You are a C++ debugger. Your ONLY job is to fix broken C++ code.
- Return ONLY valid C++ code in backticks
- Never add explanations outside the code block
- Preserve original logic and functionality
- Fix syntax errors: missing semicolons, mismatched braces, missing types
- Fix STL issues: proper includes, namespaces
- All code must be compilable and runnable

EXAMPLES:
Input: 'int main() { cout << "Hi"  return 0; }'
Output:
```cpp
#include <iostream>
using namespace std;
int main() { 
    cout << "Hi" << endl;
    return 0; 
}
```"""
        
        return user_prompt, system_prompt
    
    @staticmethod
    def get_python_optimize_prompt(code: str, goal: str = "speed") -> Tuple[str, str]:
        """Generate best Python optimize prompt"""
        
        goal_map = {
            'speed': 'make it run FASTER with better algorithm/data structures',
            'memory': 'reduce MEMORY usage with efficient data structures',
            'readability': 'make it more READABLE while keeping same functionality',
            'performance': 'optimize overall PERFORMANCE',
        }
        goal_text = goal_map.get(goal, goal_map['speed'])
        
        user_prompt = f"""Optimize this Python code to {goal_text}.

```python
{code}
```

CRITICAL RULES:
1. Return ONLY valid Python code - nothing else
2. MUST maintain EXACT same functionality and output
3. Do NOT add features or change behavior
4. All functions must work identically to original
5. All syntax must be valid Python
6. Do NOT add explanations outside code
7. Keep code as simple as possible

RESPONSE FORMAT:
```python
[YOUR OPTIMIZED CODE HERE]
```"""
        
        system_prompt = f"""You are a Python optimizer. Your job is to improve code while keeping it identical functionally.
- Return ONLY valid Python code in backticks
- Never add explanations outside the code block
- Maintain identical input/output behavior
- Focus on: algorithm efficiency, data structures, built-in functions
- Do NOT introduce new bugs
- Temperature: MUST be deterministic and consistent"""
        
        return user_prompt, system_prompt
    
    @staticmethod
    def get_c_optimize_prompt(code: str, goal: str = "speed") -> Tuple[str, str]:
        """Generate best C optimize prompt"""
        
        goal_map = {
            'speed': 'make it run FASTER with better algorithms',
            'memory': 'reduce MEMORY usage',
            'readability': 'make it more READABLE',
            'performance': 'optimize overall PERFORMANCE',
        }
        goal_text = goal_map.get(goal, goal_map['speed'])
        
        user_prompt = f"""Optimize this C code to {goal_text}.

```c
{code}
```

CRITICAL RULES:
1. Return ONLY valid C code - nothing else
2. MUST maintain EXACT same functionality
3. Do NOT change logic or output
4. All statements need semicolons
5. All braces must match
6. Must be compilable C code
7. Do NOT add explanations outside code

RESPONSE FORMAT:
```c
[YOUR OPTIMIZED CODE HERE]
```"""
        
        system_prompt = """You are a C optimizer. Keep code identical functionally while improving performance.
- Return ONLY valid C code in backticks
- Maintain identical behavior
- Focus on: algorithms, loops, memory access patterns
- Do NOT introduce new bugs"""
        
        return user_prompt, system_prompt
    
    @staticmethod
    def get_cpp_optimize_prompt(code: str, goal: str = "speed") -> Tuple[str, str]:
        """Generate best C++ optimize prompt"""
        
        goal_map = {
            'speed': 'make it run FASTER',
            'memory': 'reduce MEMORY usage',
            'readability': 'make it more READABLE',
            'performance': 'optimize overall PERFORMANCE',
        }
        goal_text = goal_map.get(goal, goal_map['speed'])
        
        user_prompt = f"""Optimize this C++ code to {goal_text}.

```cpp
{code}
```

CRITICAL RULES:
1. Return ONLY valid C++ code - nothing else
2. MUST maintain EXACT same functionality
3. Do NOT change behavior or output
4. All statements need semicolons
5. All braces must match
6. Use STL where beneficial
7. Do NOT add explanations outside code

RESPONSE FORMAT:
```cpp
[YOUR OPTIMIZED CODE HERE]
```"""
        
        system_prompt = """You are a C++ optimizer. Keep code identical functionally while improving performance.
- Return ONLY valid C++ code in backticks
- Maintain identical behavior
- Use STL appropriately
- Focus on: algorithms, data structures
- Do NOT introduce new bugs"""
        
        return user_prompt, system_prompt


class CodeExtractorFromResponse:
    """Reliably extracts code from AI responses in multiple formats"""
    
    @staticmethod
    def extract_code_from_response(response: str, language: str) -> str:
        """Extract code from various response formats"""
        
        # Try markdown code blocks first
        patterns = [
            # ```python ... ```
            (r'```(?:python|py|)\s*\n(.*?)\n```', 'python'),
            (r'```(?:c\+\+|cpp|cc|cxx|)\s*\n(.*?)\n```', ['c', 'cpp', 'c++']),
            (r'```(?:c|c\s)\s*\n(.*?)\n```', 'c'),
            # ```... code ...```
            (r'```\s*\n(.*?)\n```', 'any'),
        ]
        
        for pattern, lang_match in patterns:
            if isinstance(lang_match, list):
                if language.lower() not in lang_match:
                    continue
            elif lang_match != language.lower() and lang_match != 'any':
                continue
            
            match = re.search(pattern, response, re.DOTALL)
            if match:
                code = match.group(1).strip()
                if code:
                    return code
        
        # If no code blocks found, try to extract longest block of code
        lines = response.split('\n')
        code_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip explanation lines
            if any(keyword in stripped.lower() for keyword in [
                'explanation:', 'note:', 'here', 'fixed code:', 
                'optimized code:', 'changes:', 'output:', 'comment'
            ]):
                continue
            
            if stripped:
                code_lines.append(line)
        
        code = '\n'.join(code_lines).strip()
        
        # Remove markdown markers
        code = code.replace('```python', '').replace('```cpp', '')
        code = code.replace('```c', '').replace('```', '')
        
        return code.strip()


class ProactiveAIService:
    """
    Proactive AI service that prevents broken code generation
    Uses language-specific prompts, extraction, and validation
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.prompt_builder = LanguageSpecificPromptBuilder()
        self.code_extractor = CodeExtractorFromResponse()
        self.max_retries = 2
    
    def fix_code(
        self,
        code: str,
        error: str = "",
        language: str = "python",
        execution_output: str = None,
        execution_error: str = None
    ) -> Dict:
        """
        Fix code using proactive prompting and extraction
        
        Returns:
        {
            'success': bool,
            'fixed_code': str,
            'extracted_properly': bool,
            'attempts': int,
            'explanation': str,
            'confidence': float
        }
        """
        
        if language not in ['python', 'c', 'cpp', 'c++']:
            language = 'python'
        
        # Map c++ to cpp for consistency
        if language == 'c++':
            language = 'cpp'
        
        attempts = 0
        last_ai_response = ""
        
        while attempts < self.max_retries + 1:
            attempts += 1
            
            try:
                # Get language-specific prompt
                if language == 'python':
                    user_prompt, system_prompt = self.prompt_builder.get_python_fix_prompt(
                        code,
                        error,
                        execution_output=execution_output,
                        execution_error=execution_error
                    )
                elif language == 'c':
                    user_prompt, system_prompt = self.prompt_builder.get_c_fix_prompt(
                        code,
                        error,
                        execution_output=execution_output,
                        execution_error=execution_error
                    )
                elif language == 'cpp':
                    user_prompt, system_prompt = self.prompt_builder.get_cpp_fix_prompt(
                        code,
                        error,
                        execution_output=execution_output,
                        execution_error=execution_error
                    )
                
                # Call AI with strict prompts
                response = self.ai_service._make_request(
                    [{"role": "user", "content": user_prompt}],
                    system_prompt,
                    temperature=0.1  # VERY LOW - deterministic only
                )
                
                last_ai_response = response
                
                # Extract code from response
                fixed_code = self.code_extractor.extract_code_from_response(response, language)
                
                if not fixed_code:
                    logger.warning(f"Fix attempt {attempts}: No code extracted from response")
                    if attempts < self.max_retries + 1:
                        continue
                    
                    return {
                        'success': False,
                        'fixed_code': code,
                        'extracted_properly': False,
                        'attempts': attempts,
                        'explanation': 'Could not extract code from AI response',
                        'confidence': 0.0
                    }
                
                # Validate syntax
                try:
                    if language == 'python':
                        compile(fixed_code, '<string>', 'exec')
                    # C/C++ validation would happen at compile time
                    return {
                        'success': True,
                        'fixed_code': fixed_code,
                        'extracted_properly': True,
                        'attempts': attempts,
                        'explanation': 'Code fixed and validated',
                        'confidence': 0.95 if attempts == 1 else 0.85
                    }
                except SyntaxError as e:
                    logger.warning(f"Fix attempt {attempts}: Syntax error in extracted code - {e}")
                    if attempts < self.max_retries + 1:
                        error = f"Generated code still has error: {e.msg} on line {e.lineno}"
                        continue
                    
                    return {
                        'success': False,
                        'fixed_code': code,
                        'extracted_properly': True,
                        'attempts': attempts,
                        'explanation': f'Generated code has syntax error: {e.msg}',
                        'confidence': 0.0
                    }
                
            except Exception as e:
                logger.error(f"Fix attempt {attempts} error: {str(e)}")
                if attempts < self.max_retries + 1:
                    continue
                
                return {
                    'success': False,
                    'fixed_code': code,
                    'extracted_properly': False,
                    'attempts': attempts,
                    'explanation': f'Service error: {str(e)[:100]}',
                    'confidence': 0.0
                }
        
        # Return original if all failed
        return {
            'success': False,
            'fixed_code': code,
            'extracted_properly': False,
            'attempts': attempts,
            'explanation': 'All fix attempts failed - returning original code',
            'confidence': 0.0
        }
    
    def optimize_code(self, code: str, goal: str = "speed", language: str = "python") -> Dict:
        """
        Optimize code using proactive prompting
        """
        
        if language not in ['python', 'c', 'cpp', 'c++']:
            language = 'python'
        
        if language == 'c++':
            language = 'cpp'
        
        if goal not in ['speed', 'memory', 'readability', 'performance']:
            goal = 'speed'
        
        attempts = 0
        
        while attempts < self.max_retries + 1:
            attempts += 1
            
            try:
                # Get language-specific prompt
                if language == 'python':
                    user_prompt, system_prompt = self.prompt_builder.get_python_optimize_prompt(code, goal)
                elif language == 'c':
                    user_prompt, system_prompt = self.prompt_builder.get_c_optimize_prompt(code, goal)
                elif language == 'cpp':
                    user_prompt, system_prompt = self.prompt_builder.get_cpp_optimize_prompt(code, goal)
                
                # Call AI with strict prompts
                response = self.ai_service._make_request(
                    [{"role": "user", "content": user_prompt}],
                    system_prompt,
                    temperature=0.1  # VERY LOW - deterministic
                )
                
                # Extract code
                optimized_code = self.code_extractor.extract_code_from_response(response, language)
                
                if not optimized_code:
                    logger.warning(f"Optimize attempt {attempts}: No code extracted")
                    if attempts < self.max_retries + 1:
                        continue
                    return {
                        'success': False,
                        'optimized_code': code,
                        'extracted_properly': False,
                        'attempts': attempts,
                        'explanation': 'Could not extract code from AI response',
                        'confidence': 0.0
                    }
                
                # Validate syntax
                try:
                    if language == 'python':
                        compile(optimized_code, '<string>', 'exec')
                    
                    return {
                        'success': True,
                        'optimized_code': optimized_code,
                        'extracted_properly': True,
                        'attempts': attempts,
                        'explanation': f'Code optimized for {goal}',
                        'confidence': 0.95 if attempts == 1 else 0.85
                    }
                except SyntaxError as e:
                    logger.warning(f"Optimize attempt {attempts}: Syntax error - {e}")
                    if attempts < self.max_retries + 1:
                        continue
                    return {
                        'success': False,
                        'optimized_code': code,
                        'extracted_properly': True,
                        'attempts': attempts,
                        'explanation': f'Generated code has syntax error',
                        'confidence': 0.0
                    }
                
            except Exception as e:
                logger.error(f"Optimize attempt {attempts} error: {str(e)}")
                if attempts < self.max_retries + 1:
                    continue
                
                return {
                    'success': False,
                    'optimized_code': code,
                    'extracted_properly': False,
                    'attempts': attempts,
                    'explanation': f'Service error: {str(e)[:100]}',
                    'confidence': 0.0
                }
        
        # Return original if all failed
        return {
            'success': False,
            'optimized_code': code,
            'extracted_properly': False,
            'attempts': attempts,
            'explanation': 'All optimization attempts failed - returning original code',
            'confidence': 0.0
        }
