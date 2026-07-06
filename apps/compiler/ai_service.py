"""
Real AI Integration Service
Uses OpenAI/Claude API for intelligent code assistance
Features: Auto-fix, optimization, explanation, testing, refactoring
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
import anthropic
import openai

from .ai_router import ai_router

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    CLAUDE = "claude"


class AIConfig:
    """AI service configuration"""
    
    def __init__(self):
        self.provider = os.environ.get('AI_PROVIDER', 'openai').lower()
        
        if self.provider == 'openai':
            self.api_key = os.environ.get('OPENAI_API_KEY')
            self.model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
            self.base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        else:
            self.api_key = os.environ.get('ANTHROPIC_API_KEY')
            self.model = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        
        self.max_tokens = int(os.environ.get('AI_MAX_TOKENS', '2048'))
        self.temperature = float(os.environ.get('AI_TEMPERATURE', '0.7'))
        self.timeout = int(os.environ.get('AI_TIMEOUT', '30'))


class CodeAnalyzer:
    """Analyzes code for issues and improvements"""
    
    def __init__(self, config: AIConfig = None):
        self.config = config or AIConfig()
        self._init_client()
    
    ROUTER_TASK_MAP = {
        'explain': 'code_explanation',
        'fix': 'bug_fix',
        'optimize': 'optimization',
        'test': 'test_generation',
        'debug': 'bug_fix'
    }

    def _init_client(self):
        """Initialize AI client"""
        if self.config.provider == 'openai':
            self.client = openai.OpenAI(api_key=self.config.api_key)
        else:
            self.client = anthropic.Anthropic(api_key=self.config.api_key)
    
    def _build_prompt(self, messages: List[Dict], system_prompt: str = None) -> str:
        """Build a combined prompt text for routed providers."""
        parts = []
        if system_prompt:
            parts.append(system_prompt)

        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            parts.append(f"{role.capitalize()}: {content}")

        return '\n\n'.join(parts).strip()

    def _route_task(self, task_type: str, messages: List[Dict], system_prompt: str = None) -> Optional[str]:
        """Route the task to the preferred provider and return raw text if successful."""
        try:
            prompt = self._build_prompt(messages, system_prompt)
            response = ai_router.route_task(task_type, prompt)
            if response.get('success'):
                return response.get('result')
            logger.warning(f"AI router did not return success for {task_type}: {response.get('error')}")
        except Exception as e:
            logger.warning(f"AI router routing failed for {task_type}: {e}")
        return None

    def _make_request(self, messages: List[Dict], system_prompt: str = None, task_type: str = None) -> str:
        """
        Make API request to AI provider
        """
        if task_type:
            routed = self._route_task(task_type, messages, system_prompt)
            if routed is not None:
                return routed

        try:
            if self.config.provider == 'openai':
                return self._call_openai(messages, system_prompt)
            else:
                return self._call_claude(messages, system_prompt)
        except Exception as e:
            logger.error(f"AI API error: {str(e)}")
            raise
    
    def _call_openai(self, messages: List[Dict], system_prompt: str = None) -> str:
        """Call OpenAI API"""
        system_messages = []
        if system_prompt:
            system_messages.append({"role": "system", "content": system_prompt})
        
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=system_messages + messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            timeout=self.config.timeout,
        )
        
        return response.choices[0].message.content
    
    def _call_claude(self, messages: List[Dict], system_prompt: str = None) -> str:
        """Call Claude API"""
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt or "You are an expert Python programmer and code reviewer.",
            messages=messages,
        )
        
        return response.content[0].text
    
    def explain_code(
        self,
        code: str,
        context: str = None,
        execution_output: str = None,
        execution_error: str = None
    ) -> Dict:
        """
        Explain what the code does with examples
        
        Returns:
            {
                'summary': str,
                'detailed_explanation': str,
                'key_concepts': List[str],
                'time_complexity': str,
                'space_complexity': str,
            }
        """
        full_context = ''
        if context:
            full_context += f"Additional context: {context}"
        if execution_output:
            full_context += ('\n\n' if full_context else '') + f"Program output:\n{execution_output}"
        if execution_error:
            full_context += ('\n\n' if full_context else '') + f"Execution error:\n{execution_error}"

        prompt = f"""Analyze this Python code and provide a comprehensive explanation:

```python
{code}
```

{f'Additional context: {context}' if context else ''}

Provide your response in this JSON format (valid JSON only, no markdown):
{{
    "summary": "One-line summary of what this code does",
    "detailed_explanation": "Paragraph explaining the logic step-by-step",
    "key_concepts": ["concept1", "concept2", ...],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
    "example_walkthrough": "Walk through a simple example"
}}"""
        
        system_prompt = "You are an expert Python programmer. Analyze code and provide clear explanations suitable for learners."
        
        response = self._make_request(
            [{"role": "user", "content": prompt}],
            system_prompt,
            task_type='code_explanation'
        )
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "summary": response[:200],
            "detailed_explanation": response,
            "key_concepts": [],
            "time_complexity": "Unknown",
            "space_complexity": "Unknown"
        }
    
    def auto_fix_code(
        self,
        code: str,
        error: str = None,
        test_failures: List[str] = None,
        execution_output: str = None,
        execution_error: str = None,
        language: str = "python"
    ) -> Dict:
        """
        Automatically fix code based on errors or test failures
        Maintains the language of the code
        
        Returns:
            {
                'fixed_code': str,
                'changes': List[str],
                'explanation': str,
                'issues_found': List[str],
                'confidence': float (0-1)
            }
        """
        error_context = ""
        if error:
            error_context += f"\n\nError encountered:\n{error}"
        if test_failures:
            error_context += f"\n\nTest failures:\n" + "\n".join(test_failures)
        if execution_output:
            error_context += f"\n\nProgram output:\n{execution_output}"
        if execution_error:
            error_context += f"\n\nExecution error:\n{execution_error}"
        
        # Map language to code block syntax
        lang_map = {
            'python': 'python',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
        }
        lang_block = lang_map.get(language.lower(), language.lower())
        
        prompt = f"""Fix the following {language} code. If there are errors or test failures mentioned, fix those issues:

```{lang_block}
{code}
```{error_context}

CRITICAL REQUIREMENTS:
- Return ONLY valid, compilable {language} code that works correctly
- MUST maintain the same language ({language})
- MUST preserve original intent and functionality
- Do NOT convert to another language
- Do NOT introduce new bugs
- Fix all issues mentioned in the error

Provide your response in this JSON format (valid JSON only):
{{
    "fixed_code": "The corrected code in {language}",
    "changes": ["Change 1", "Change 2", ...],
    "explanation": "Explanation of what was wrong and how it was fixed",
    "issues_found": ["Issue 1", "Issue 2", ...],
    "confidence": 0.95
}}"""
        
        system_prompt = f"""You are an expert {language} debugger. Your job is to fix code errors while maintaining functionality.
- CRITICAL: Return ONLY valid, runnable {language} code
- Keep the same language ({language}) - do NOT convert to another language
- Maintain original intent and functionality
- Be careful with logic changes
- Add comments for non-obvious fixes
- Fix all reported errors
- Temperature: 0.2 for consistency"""
        
        response = self._make_request(
            [{"role": "user", "content": prompt}],
            system_prompt,
            task_type='bug_fix'
        )
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result['confidence'] = result.get('confidence', 0.85)
                return result
        except Exception as e:
            logger.error(f"Failed to parse auto-fix response: {e}")
        
        return {
            "fixed_code": code,
            "changes": ["Unable to auto-fix"],
            "explanation": "Could not parse AI response",
            "issues_found": [],
            "confidence": 0.0
        }
    
    def optimize_code(self, code: str, optimization_goal: str = None, language: str = "python") -> Dict:
        """
        Suggest optimizations for the code with validation
        Maintains the language of the code
        
        Args:
            code: Code to optimize
            optimization_goal: "speed", "memory", "readability", or None for all
            language: Programming language (python, c, cpp, etc.)
        
        Returns:
            {
                'optimized_code': str,
                'optimizations': List[{name, description, impact}],
                'performance_improvement': str,
                'explanation': str,
                'confidence': float
            }
        """
        goal_text = ""
        if optimization_goal:
            goal_text = f"Focus on {optimization_goal} optimization. "
        
        # Map language to code block syntax
        lang_map = {
            'python': 'python',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
        }
        lang_block = lang_map.get(language.lower(), language.lower())
        
        prompt = f"""{goal_text}Analyze and optimize this {language} code:

```{lang_block}
{code}
```

CRITICAL REQUIREMENTS:
- Return ONLY valid, compilable {language} code that can run immediately
- Maintain EXACT functionality and output (same input → same output)
- Do NOT convert to another language
- Do NOT introduce new bugs or errors
- Do NOT change the algorithm unless absolutely necessary for performance

Provide your response in this JSON format (valid JSON only):
{{
    "optimized_code": "The optimized version in {language}",
    "optimizations": [
        {{
            "name": "Optimization name",
            "description": "What was optimized",
            "impact": "High/Medium/Low",
            "explanation": "Why this helps"
        }}
    ],
    "performance_improvement": "Estimated improvement (e.g., '40% faster')",
    "explanation": "Overall optimization strategy",
    "confidence": 0.95
}}"""
        
        system_prompt = f"""You are a {language} performance optimization expert.
- CRITICAL: Return ONLY valid, compilable {language} code
- Do NOT convert to another language - keep everything in {language}
- Maintain identical functionality and behavior
- Provide practical optimizations that improve performance
- Focus on: algorithm efficiency, data structures, built-in functions, caching
{f'- Prioritize: {optimization_goal}' if optimization_goal else ''}
- Temperature: 0.2 for consistency"""
        
        response = self._make_request(
            [{"role": "user", "content": prompt}],
            system_prompt,
            task_type='optimization'
        )
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result['confidence'] = result.get('confidence', 0.85)
                return result
        except Exception as e:
            logger.error(f"Failed to parse optimize response: {e}")
        
        return {
            "optimized_code": code,
            "optimizations": [],
            "performance_improvement": "Unable to optimize",
            "explanation": "Could not parse AI response",
            "confidence": 0.0
        }
    
    def generate_tests(self, code: str, function_signature: str = None) -> Dict:
        """
        Generate unit tests for the code
        
        Returns:
            {
                'test_code': str,
                'test_cases': List[{input, expected_output, description}],
                'edge_cases': List[str],
                'explanation': str
            }
        """
        prompt = f"""Generate comprehensive unit tests for this Python code:

```python
{code}
```

{f'Function signature: {function_signature}' if function_signature else ''}

Provide your response in this JSON format (valid JSON only):
{{
    "test_code": "Complete pytest test code",
    "test_cases": [
        {{
            "input": "input values",
            "expected_output": "what should be returned",
            "description": "what this tests"
        }}
    ],
    "edge_cases": ["Edge case 1", "Edge case 2"],
    "explanation": "Testing strategy used"
}}"""
        
        system_prompt = """You are a Python testing expert using pytest.
Generate comprehensive tests that cover:
- Normal cases
- Edge cases (empty, large, negative)
- Error conditions
Write clean, well-documented tests."""
        
        response = self._make_request(
            [{"role": "user", "content": prompt}],
            system_prompt,
            task_type='test_generation'
        )
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "test_code": "",
            "test_cases": [],
            "edge_cases": [],
            "explanation": response[:500]
        }
    
    def refactor_code(self, code: str, refactoring_type: str = None) -> Dict:
        """
        Refactor code for better structure and maintainability
        
        Args:
            code: Python code to refactor
            refactoring_type: "extract_functions", "design_patterns", "clean_code", or None
        
        Returns:
            {
                'refactored_code': str,
                'changes': List[str],
                'design_patterns_applied': List[str],
                'explanation': str,
                'before_after_comparison': str
            }
        """
        type_text = ""
        if refactoring_type:
            type_text = f"Focus on {refactoring_type}. "
        
        prompt = f"""{type_text}Refactor this Python code for better structure and maintainability:

```python
{code}
```

Provide your response in this JSON format (valid JSON only):
{{
    "refactored_code": "The refactored version",
    "changes": ["Change 1", "Change 2"],
    "design_patterns_applied": ["Pattern 1", "Pattern 2"],
    "explanation": "Why these changes improve the code",
    "improvements": "List of improvements made"
}}"""
        
        system_prompt = """You are a software architect expert in code quality and design patterns.
Apply SOLID principles, DRY, and clean code practices.
Extract functions, use meaningful names, improve structure.
Maintain the original functionality while improving readability and maintainability."""
        
        response = self._make_request(
            [{"role": "user", "content": prompt}],
            system_prompt
        )
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "refactored_code": code,
            "changes": [],
            "design_patterns_applied": [],
            "explanation": response[:500],
            "improvements": []
        }
    
    def debug_code(
        self,
        code: str,
        error: str,
        traceback: str = None,
        execution_output: str = None,
        execution_error: str = None
    ) -> Dict:
        """
        Debug code and provide detailed fixes
        
        Returns:
            {
                'root_cause': str,
                'fixed_code': str,
                'explanation': str,
                'debugging_tips': List[str],
                'similar_issues': List[str]
            }
        """
        prompt = f"""Debug this Python code that's producing an error:

```python
{code}
```

Error message: {error}
{f'Traceback: {traceback}' if traceback else ''}
"""
        if execution_output:
            prompt += f"\n\nProgram output:\n{execution_output}"
        if execution_error:
            prompt += f"\n\nExecution error:\n{execution_error}"

        prompt += """\n\nProvide your response in this JSON format (valid JSON only):
{{
    "root_cause": "What's actually causing the error",
    "fixed_code": "The corrected code",
    "explanation": "Step-by-step explanation of the fix",
    "debugging_tips": ["Tip 1", "Tip 2"],
    "similar_issues": ["Similar issue 1", "Similar issue 2"]
}}"""
        
        system_prompt = """You are an expert Python debugger.
Identify the root cause of errors and provide clear fixes.
Explain why the error occurred and how to prevent similar issues.
Be educational in your explanations."""
        
        response = self._make_request(
            [{"role": "user", "content": prompt}],
            system_prompt,
            task_type='bug_fix'
        )
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "root_cause": "Unable to determine",
            "fixed_code": code,
            "explanation": response[:500],
            "debugging_tips": [],
            "similar_issues": []
        }
    
    def review_code(self, code: str, review_focus: List[str] = None) -> Dict:
        """
        Comprehensive code review
        
        Args:
            code: Code to review
            review_focus: Focus areas like ["performance", "security", "readability"]
        
        Returns:
            {
                'issues': List[{severity, category, description, line, suggestion}],
                'strengths': List[str],
                'overall_score': int (0-100),
                'summary': str
            }
        """
        focus_text = ""
        if review_focus:
            focus_text = f"\nFocus on: {', '.join(review_focus)}"
        
        prompt = f"""Perform a code review of this Python code:{focus_text}

```python
{code}
```

Provide your response in this JSON format (valid JSON only):
{{
    "issues": [
        {{
            "severity": "critical/high/medium/low",
            "category": "performance/security/style/logic",
            "description": "What's wrong",
            "suggestion": "How to fix it"
        }}
    ],
    "strengths": ["Good practice 1", "Good practice 2"],
    "overall_score": 75,
    "summary": "Overall assessment"
}}"""
        
        system_prompt = """You are a senior code reviewer.
Identify issues in: logic, performance, security, style, maintainability.
Be constructive and educational.
Rate code from 0-100 based on quality standards."""
        
        response = self._make_request(
            [{"role": "user", "content": prompt}],
            system_prompt
        )
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "issues": [],
            "strengths": [],
            "overall_score": 50,
            "summary": response[:500]
        }
    
    def chat_assistant(self, messages: List[Dict], code_context: str = None) -> str:
        """
        Multi-turn chat assistant with code context
        
        Args:
            messages: List of message dicts with "role" and "content"
            code_context: Current code being discussed
        
        Returns:
            Assistant's response
        """
        if code_context:
            messages[0]['content'] = f"""Current code context:
```python
{code_context}
```

{messages[0]['content']}"""
        
        system_prompt = """You are an expert Python programming assistant.
Help users understand code, fix bugs, optimize performance, and learn best practices.
Always provide practical, tested advice.
Ask clarifying questions when needed."""
        
        return self._make_request(messages, system_prompt)


class AIIntegrationService:
    """High-level service for AI integrations"""
    
    def __init__(self):
        self.config = AIConfig()
        self.analyzer = CodeAnalyzer(self.config)
    
    def process_code(self, code: str, action: str, **kwargs) -> Dict:
        """
        Process code with specified action
        
        Actions:
        - explain
        - fix
        - optimize
        - test
        - refactor
        - debug
        - review
        - chat
        """
        handlers = {
            'explain': self.analyzer.explain_code,
            'fix': self.analyzer.auto_fix_code,
            'optimize': self.analyzer.optimize_code,
            'test': self.analyzer.generate_tests,
            'refactor': self.analyzer.refactor_code,
            'debug': self.analyzer.debug_code,
            'review': self.analyzer.review_code,
            'chat': self.analyzer.chat_assistant,
        }
        
        handler = handlers.get(action)
        if not handler:
            return {'error': f'Unknown action: {action}'}
        
        try:
            return handler(code, **kwargs)
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            return {'error': str(e)}


# Singleton instance
_ai_service = None


def get_ai_service() -> AIIntegrationService:
    """Get or create AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIIntegrationService()
    return _ai_service
