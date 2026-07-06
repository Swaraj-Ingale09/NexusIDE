"""
Multi-Provider AI Integration
Uses Groq (primary), OpenRouter, Nvidia NIM with proper prompt engineering
Each call gives unique, contextual responses
"""

import os
import json
import requests
import logging
from typing import Dict, List, Optional
from enum import Enum
import random
import openai

logger = logging.getLogger(__name__)


class GroqAI:
    """Groq API integration with key pool rotation.

    Uses GroqKeyPool to automatically rotate through multiple API keys.
    When a key hits rate limits (429), the pool switches to the next available key.
    """

    def __init__(self):
        from apps.compiler.groq_key_pool import get_groq_pool
        self.pool = get_groq_pool()
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama-3.3-70b-versatile"
        # Fallback key for when pool is empty
        self.fallback_key = os.environ.get('GROQ_API_KEY')

    def _call(self, messages, max_tokens=2048, temperature=0.3, user_id=None):
        """Make a Groq API call with automatic key rotation.

        Tries up to N keys from the pool. If all fail, returns None.
        """
        import openai

        max_attempts = min(len(self.pool.keys) if self.pool.keys else 1, 5)
        last_error = None

        for attempt in range(max_attempts):
            # Get best available key from pool
            key_state = self.pool.get_key_for_user(user_id) if user_id else self.pool.get_key()

            if not key_state:
                # Pool exhausted — try fallback key
                if self.fallback_key:
                    try:
                        client = openai.OpenAI(api_key=self.fallback_key, base_url=self.base_url)
                        response = client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            timeout=20,
                        )
                        return response.choices[0].message.content
                    except Exception as e:
                        logger.error("GroqAI fallback key failed: %s", e)
                        return None
                return None

            try:
                client = openai.OpenAI(api_key=key_state.key, base_url=self.base_url)
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=20,
                )
                # Record success — estimate tokens from response
                tokens_used = getattr(response.usage, 'total_tokens', 0) if response.usage else 0
                self.pool.record_success(key_state, tokens_used)
                return response.choices[0].message.content

            except Exception as e:
                last_error = str(e)
                self.pool.record_failure(key_state, last_error)
                logger.warning("GroqAI key '%s' failed (attempt %d/%d): %s",
                             key_state.name, attempt + 1, max_attempts, last_error[:100])
                continue

        logger.error("GroqAI: all %d attempts failed. Last error: %s", max_attempts, last_error)
        return None
    
    def fix(self, code: str, error: str = None, language: str = "python") -> str:
        lang_map = {'python': 'python', 'c': 'c', 'cpp': 'cpp', 'c++': 'cpp'}
        lang_block = lang_map.get(language.lower(), language.lower())
        
        system = f"You are an expert {language} programmer. Fix bugs and return only the corrected code."
        user = f"Fix this {language} code. Return ONLY the fixed code in a ```{lang_block}``` block.\n\n"
        if error:
            user += f"Error:\n{error}\n\n"
        user += f"Code:\n```{lang_block}\n{code}\n```"
        
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ], max_tokens=2048, temperature=0.3)
    
    def explain(self, code: str, language: str = "python") -> str:
        system = f"You are an expert {language} educator. Explain code clearly and concisely."
        user = f"Explain this {language} code step by step:\n\n```{language.lower()}\n{code}\n```"
        
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ], max_tokens=1500, temperature=0.5)
    
    def optimize(self, code: str, goal: str = "speed", language: str = "python") -> str:
        lang_map = {'python': 'python', 'c': 'c', 'cpp': 'cpp', 'c++': 'cpp'}
        lang_block = lang_map.get(language.lower(), language.lower())
        
        system = f"You are an expert {language} performance engineer. Optimize code for {goal}."
        user = f"Optimize this {language} code for {goal}. Return ONLY the optimized code in a ```{lang_block}``` block with brief comments.\n\n```{lang_block}\n{code}\n```"
        
        return self._call([
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ], max_tokens=2048, temperature=0.3)
    
    def generate(self, prompt: str) -> str:
        return self._call([
            {"role": "system", "content": "You are an expert programmer. Generate clean, efficient code."},
            {"role": "user", "content": prompt}
        ], max_tokens=2048, temperature=0.5)
    
    def review(self, code: str) -> str:
        return self._call([
            {"role": "system", "content": "You are a senior code reviewer. Review code for bugs, performance, and best practices."},
            {"role": "user", "content": f"Review this code:\n\n```\n{code}\n```"}
        ], max_tokens=1500, temperature=0.4)
    
    def suggest(self, code: str, context: str = None) -> str:
        user = f"Suggest improvements for this code:\n\n```\n{code}\n```"
        if context:
            user = f"Context: {context}\n\n{user}"
        return self._call([
            {"role": "system", "content": "You are a coding assistant. Suggest practical improvements."},
            {"role": "user", "content": user}
        ], max_tokens=1024, temperature=0.5)


class OpenRouterAI:
    """OpenRouter API integration - Each call is UNIQUE"""
    
    def __init__(self):
        self.api_key = os.environ.get('OPENROUTER_API_KEY')
        self.base_url = "https://openrouter.ai/api/v1"
        # Using OpenRouter's "auto" routing for best model
        self.model = "openrouter/auto"
    
    def fix(self, code: str, error: str = None, language: str = "python") -> str:
        """Fix code in the specified language - UNIQUE response each time"""
        # Map language to code block syntax
        lang_map = {
            'python': 'python',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
        }
        lang_block = lang_map.get(language.lower(), language.lower())
        
        prompt = f"""Fix the following {language} code. Return ONLY the corrected code in {language}, no explanations.

{"Error: " + error if error else ""}

Original code:
```{lang_block}
{code}
```

Fixed code (MUST be in {language}):
```{lang_block}"""
        
        return self._call_api(prompt, max_tokens=2048, temperature=0.3)
    
    def explain(self, code: str, language: str = "python") -> str:
        """Explain code with different perspective each time"""
        perspectives = [
            f"Explain what this {language} code does step by step, like teaching a beginner",
            f"Analyze this {language} code and explain its purpose, logic flow, and any edge cases",
            f"Break down this {language} code line by line and explain each part's function",
            f"Explain how this {language} code works and what problem it solves",
        ]
        perspective = random.choice(perspectives)
        
        prompt = f"""{perspective}

{language} code:
```{language.lower()}
{code}
```

Explanation:"""
        
        return self._call_api(prompt, max_tokens=1024, temperature=0.8)
    
    def optimize(self, code: str, goal: str = "speed", language: str = "python") -> str:
        """Optimize code in the specified language - UNIQUE optimization each time"""
        # Map language to code block syntax
        lang_map = {
            'python': 'python',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
        }
        lang_block = lang_map.get(language.lower(), language.lower())
        
        goals = {
            'speed': f'Make this {language} code run FASTER. Focus on algorithmic improvements.',
            'memory': f'Reduce MEMORY USAGE in this {language} code. Optimize for space complexity.',
            'readability': f'Improve READABILITY of this {language} code. Make it cleaner and more maintainable.',
            'performance': f'Optimize this {language} code for overall performance.',
        }
        
        goal_text = goals.get(goal, goals['speed'])
        
        prompt = f"""{goal_text}

Original code:
```{lang_block}
{code}
```

Optimized code (MUST be in {language}):
```{lang_block}"""
        
        return self._call_api(prompt, max_tokens=2048, temperature=0.5)
    
    def generate(self, prompt: str, language: str = 'python') -> str:
        """Generate code from description - ChatGPT-like"""
        full_prompt = f"""CRITICAL: You must output ONLY working {language} code. No explanations, no markdown, no analysis.

User requirement: {prompt}

OUTPUT ONLY {language.upper()} CODE (no explanations):"""
        
        return self._call_api(full_prompt, max_tokens=3000, temperature=0.7)
    
    def review(self, code: str, language: str = 'python') -> str:
        """Review code - UNIQUE review each time"""
        review_types = [
            f"Perform a code review focusing on performance and best practices for this {language} code",
            f"Analyze this {language} code for bugs, edge cases, and potential issues",
            f"Review this {language} code for security, maintainability, and {language} style",
            f"Critique this {language} code and suggest specific improvements",
        ]
        review_type = random.choice(review_types)
        
        prompt = f"""{review_type}

{language} code:
```{language}
{code}
```

Review:"""
        
        return self._call_api(prompt, max_tokens=1500, temperature=0.7)
    
    def suggest(self, code: str, context: str = None, language: str = 'python') -> str:
        """Suggest next line of code"""
        prompt = f"""Based on this {language} code, what should be the next logical line(s)?
Provide ONLY the next line(s) of code, no explanations.

Current code:
```{language}
{code}
```

{"Context: " + context if context else ""}

Next line(s):"""
        
        return self._call_api(prompt, max_tokens=256, temperature=0.6)
    
    def _call_api(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Call OpenRouter API with HIGH VARIATION for unique responses"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nexusIDE.dev",
                    "X-Title": "NexusIDE",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.95,
                    "top_k": 40,
                    "frequency_penalty": 0.5,
                    "presence_penalty": 0.5,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenRouter error {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"OpenRouter request error: {str(e)}")
            return None

    def stream(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7):
        """
        Stream response from OpenRouter using SSE.
        Yields text chunks as they arrive.
        """
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nexusIDE.dev",
                    "X-Title": "NexusIDE",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.95,
                    "frequency_penalty": 0.5,
                    "presence_penalty": 0.5,
                    "stream": True,
                },
                stream=True,
                timeout=60
            )

            if response.status_code != 200:
                yield f"[ERROR] API returned {response.status_code}"
                return

            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode('utf-8') if isinstance(raw_line, bytes) else raw_line
                if line.startswith('data: '):
                    data = line[6:]
                    if data.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk['choices'][0].get('delta', {})
                        text = delta.get('content', '')
                        if text:
                            yield text
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        except Exception as e:
            logger.error(f"OpenRouter stream error: {str(e)}")
            yield f"[ERROR] {str(e)}"


class NvidiaNIMAI:
    """Nvidia NIM integration - Each call is UNIQUE"""
    
    def __init__(self):
        self.api_key = os.environ.get('NVIDIA_NIM_API_KEY')
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model = "nvidia/llama-3.1-nemotron-70b-instruct"
    
    def fix(self, code: str, error: str = None, language: str = "python") -> str:
        """Fix code in the specified language - UNIQUE response each time"""
        lang_map = {
            'python': 'python',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
        }
        lang_block = lang_map.get(language.lower(), language.lower())
        
        prompt = f"""Fix the following {language} code. Return ONLY the corrected code in {language}.

{"Error message: " + error if error else "Fix any bugs or issues you find."}

Code:
```{lang_block}
{code}
```

Fixed code (MUST be in {language}):"""
        
        return self._call_api(prompt, max_tokens=2048, temperature=0.3)
    
    def explain(self, code: str, language: str = "python") -> str:
        """Explain code with different approach each time"""
        approaches = [
            f"Explain this {language} code in simple terms for a beginner",
            f"Provide a detailed technical analysis of this {language} code",
            f"Explain the algorithm and logic flow of this {language} code",
            f"Break down this {language} code and explain what each part does",
        ]
        approach = random.choice(approaches)
        
        prompt = f"""{approach}:

```{language.lower()}
{code}
```

Explanation:"""
        
        return self._call_api(prompt, max_tokens=1024, temperature=0.8)
    
    def optimize(self, code: str, goal: str = "speed", language: str = "python") -> str:
        """Optimize code in the specified language - UNIQUE optimization each time"""
        lang_map = {
            'python': 'python',
            'c': 'c',
            'cpp': 'cpp',
            'c++': 'cpp',
        }
        lang_block = lang_map.get(language.lower(), language.lower())
        
        goals = {
            'speed': f'Optimize this {language} code for SPEED and performance',
            'memory': f'Optimize this {language} code for MEMORY EFFICIENCY',
            'readability': f'Make this {language} code more READABLE and MAINTAINABLE',
            'performance': f'Optimize this {language} code for overall PERFORMANCE',
        }
        
        goal_text = goals.get(goal, goals['speed'])
        
        prompt = f"""Optimize this {language} code: {goal_text}

Original:
```{lang_block}
{code}
```

Optimized code (MUST be in {language}):"""
        
        return self._call_api(prompt, max_tokens=2048, temperature=0.5)
    
    def generate(self, prompt: str) -> str:
        """Generate code from description - ChatGPT-like"""
        full_prompt = f"""CRITICAL: You must output ONLY working Python code. No explanations, no markdown, no analysis.

User requirement: {prompt}

OUTPUT ONLY CODE (no explanations):"""
        
        return self._call_api(full_prompt, max_tokens=3000, temperature=0.7)
    
    def review(self, code: str) -> str:
        """Review code - UNIQUE review each time"""
        review_focus = random.choice([
            "Focus on performance and efficiency",
            "Focus on bugs and edge cases",
            "Focus on security and best practices",
            "Focus on code style and maintainability",
        ])
        
        prompt = f"""Review this Python code ({review_focus}):

```python
{code}
```

Review:"""
        
        return self._call_api(prompt, max_tokens=1500, temperature=0.7)
    
    def suggest(self, code: str, context: str = None) -> str:
        """Suggest next line of code"""
        prompt = f"""What should be the next line(s) of Python code after this?
Provide ONLY the code, no explanations.

```python
{code}
```

{"Context: " + context if context else ""}

Next:"""
        
        return self._call_api(prompt, max_tokens=256, temperature=0.6)
    
    def _call_api(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Call Nvidia NIM API with HIGH VARIATION"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.95,  # High diversity
                    "top_k": 40,
                    "frequency_penalty": 0.5,
                    "presence_penalty": 0.5,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"Nvidia NIM error {response.status_code}")
                return None
        
        except Exception as e:
            logger.error("Nvidia NIM request failed")
            return None


class FallbackResponses:
    """Fallback responses when both APIs are exhausted"""
    
    @staticmethod
    def fix_fallback(code: str, error: str = None, language: str = 'python') -> str:
        """Return a helpful fix suggestion when API is down"""
        return f"""
API services are currently busy or exhausted.

Here's what you can try to fix your code:

1. Check the error message carefully
2. Look at line numbers mentioned in the error
3. Common fixes:
   - Missing colons (:) after if/for/while/def
   - Incorrect indentation (must be consistent)
   - Undefined variables or wrong function names
   - Missing closing brackets or parentheses

Your code:
```{language}
{code}
```

Error: {error if error else "Unknown error"}

Please try again in a moment, or review the code manually using the checklist above.
"""
    
    @staticmethod
    def explain_fallback(code: str, language: str = 'python') -> str:
        """Return basic explanation when API is down"""
        lines = len(code.strip().split('\n'))
        return f"""
AI services are temporarily unavailable.

Here's a basic analysis of your code:

**Code Statistics:**
- Lines of code: {lines}
- Characters: {len(code)}

**What you can do:**
1. Review the code structure manually
2. Look for syntax errors
3. Check for undefined variables
4. Verify function/method names are correct
5. Ensure proper indentation

**Your code:**
```{language}
{code}
```

The AI service will be back online shortly. Please try again later.
"""
    
    @staticmethod
    def optimize_fallback(code: str, language: str = 'python') -> str:
        """Return basic optimization suggestions when API is down"""
        return f"""
AI optimization service is currently unavailable.

Here are general optimization tips:

**Performance:**
- Use list comprehensions instead of loops (Python)
- Avoid nested loops when possible
- Use built-in functions (map, filter, etc.)
- Cache results of expensive operations

**Readability:**
- Add comments explaining complex logic
- Use meaningful variable names
- Break functions into smaller pieces
- Follow language style guides

**Your code:**
```{language}
{code}
```

Please try again when the service is restored.
"""
    
    @staticmethod
    def generate_fallback(prompt: str, language: str = 'python') -> str:
        """Return template code when API is down"""
        return f"""
Code generation service is temporarily unavailable.

**Your request:** {prompt}

Please try again when the service is restored.
"""
    
    @staticmethod
    def review_fallback(code: str, language: str = 'python') -> str:
        """Return basic review when API is down"""
        return f"""
Code review service is temporarily unavailable.

**Manual review checklist:**

- Does the code follow {language} style guidelines?
- Are all variables properly defined?
- Are there any obvious bugs?
- Is error handling included?
- Are function docstrings present?
- Is the code efficient?
- Are there security concerns?

**Your code:**
```python
{code}
```

Please review manually or try again when service is available.
"""


class FallbackCache:
    """Cache responses to serve during API outages"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
    
    def get(self, key: str):
        """Get cached response"""
        if key in self.cache:
            import time
            timestamp, value = self.cache[key]
            if time.time() - timestamp < self.cache_timeout:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: str):
        """Cache a response"""
        import time
        self.cache[key] = (time.time(), value)
    
    def clear_expired(self):
        """Clear expired cache entries"""
        import time
        current_time = time.time()
        expired_keys = [
            k for k, (ts, _) in self.cache.items()
            if current_time - ts >= self.cache_timeout
        ]
        for k in expired_keys:
            del self.cache[k]


# Global cache instance
_fallback_cache = FallbackCache()


class MultiProviderAI:
    """Smart router between multiple AI providers - UNIQUE responses every time"""
    
    def __init__(self):
        self.groq = None
        self.openrouter = None
        self.nvidia = None
        self.setup_providers()
    
    def setup_providers(self):
        """Initialize available providers (Groq primary, OpenRouter fallback)"""
        # Check for key pool (GROQ_API_KEYS) or single key (GROQ_API_KEY)
        has_groq_keys = os.environ.get('GROQ_API_KEYS') or os.environ.get('GROQ_API_KEY')
        if has_groq_keys:
            try:
                from apps.compiler.groq_key_pool import get_groq_pool
                pool = get_groq_pool()
                pool.load_from_env()
                self.groq = GroqAI()
                logger.info("[OK] Groq initialized with %d keys in pool", len(pool.keys))
            except Exception as e:
                logger.error(f"Groq init failed: {e}")
        
        if os.environ.get('OPENROUTER_API_KEY'):
            try:
                self.openrouter = OpenRouterAI()
                logger.info("[OK] OpenRouter initialized (fallback)")
            except Exception as e:
                logger.error(f"OpenRouter init failed: {e}")
        
        # Nvidia NIM disabled — API key/endpoint invalid (404 on every call)
        # To re-enable, fix the NVIDIA_NIM_API_KEY in .env and uncomment below:
        # if os.environ.get('NVIDIA_NIM_API_KEY'):
        #     try:
        #         self.nvidia = NvidiaNIMAI()
        #         logger.info("[OK] Nvidia NIM initialized")
        #     except Exception as e:
        #         logger.error(f"Nvidia NIM init failed: {e}")
    
    def auto_fix(self, code: str, error: str = None, language: str = 'python') -> Dict:
        """Auto-fix - Gets UNIQUE fix each time or fallback"""
        result = self._call_provider('fix', code, error, language=language)
        provider = self._get_last_provider_used()
        
        if result is None:
            # Both APIs failed - use fallback
            result = FallbackResponses.fix_fallback(code, error, language=language)
            provider = 'fallback'
            success = False
        else:
            success = True
        
        return {
            'success': success,
            'fixed_code': result,
            'provider': provider,
            'type': 'auto_fix'
        }
    
    def explain_inline(self, code: str, language: str = 'python') -> Dict:
        """Explain code - Gets UNIQUE explanation or fallback"""
        result = self._call_provider('explain', code, language=language)
        provider = self._get_last_provider_used()
        
        if result is None:
            # Both APIs failed - use fallback
            result = FallbackResponses.explain_fallback(code, language=language)
            provider = 'fallback'
            success = False
        else:
            success = True
        
        return {
            'success': success,
            'explanation': result,
            'provider': provider,
            'type': 'explain'
        }
    
    def optimize_inline(self, code: str, goal: str = 'speed', language: str = 'python') -> Dict:
        """Optimize code - Gets UNIQUE optimization or fallback"""
        result = self._call_provider('optimize', code, goal, language=language)
        provider = self._get_last_provider_used()
        
        if result is None:
            # Both APIs failed - use fallback
            result = FallbackResponses.optimize_fallback(code, language=language)
            provider = 'fallback'
            success = False
        else:
            success = True
        
        return {
            'success': success,
            'suggestion': result,
            'provider': provider,
            'type': 'optimize'
        }
    
    def generate_code(self, prompt: str, language: str = 'python') -> Dict:
        """Generate code - ChatGPT-like or fallback"""
        result = self._call_provider('generate', prompt, language=language)
        provider = self._get_last_provider_used()
        
        if result is None:
            # Both APIs failed - use fallback
            result = FallbackResponses.generate_fallback(prompt)
            provider = 'fallback'
            success = False
        else:
            success = True
        
        return {
            'success': success,
            'generated_code': result,
            'provider': provider,
            'type': 'generate'
        }
    
    def review_inline(self, code: str) -> Dict:
        """Review code - Gets UNIQUE review or fallback"""
        result = self._call_provider('review', code)
        provider = self._get_last_provider_used()
        
        if result is None:
            # Both APIs failed - use fallback
            result = FallbackResponses.review_fallback(code)
            provider = 'fallback'
            success = False
        else:
            success = True
        
        return {
            'success': success,
            'review': result,
            'provider': provider,
            'type': 'review'
        }
    
    def suggest_improvements(self, code: str) -> Dict:
        """Suggest improvements - Gets UNIQUE suggestions or fallback"""
        result = self._call_provider('review', code)
        provider = self._get_last_provider_used()
        
        if result is None:
            # Both APIs failed - use fallback
            result = FallbackResponses.review_fallback(code)
            provider = 'fallback'
            success = False
        else:
            success = True
        
        return {
            'success': success,
            'improvements': result,
            'provider': provider,
            'type': 'suggest'
        }
    
    def suggest_next(self, code: str, context: str = None) -> Dict:
        """Suggest next line"""
        result = self._call_provider('suggest', code, context)
        provider = self._get_last_provider_used()
        return {
            'success': result is not None,
            'suggestion': result,
            'provider': provider,
            'type': 'suggest'
        }
    
    def _get_last_provider_used(self) -> str:
        """Return the name of the last provider used"""
        if hasattr(self, '_last_provider'):
            return self._last_provider
        return "unknown"

    def stream_action(self, action: str, code: str, extra: str = '', language: str = 'python'):
        """
        Stream a response for the given action.
        Yields text chunks. Falls back to non-streaming if no provider supports it.
        """
        provider = self.openrouter  # Use OpenRouter for streaming (supports SSE)
        if not provider:
            yield "AI provider not configured."
            return

        prompts = {
            'explain': f"Explain what this {language} code does step by step:\n\n```{language}\n{code}\n```\n\nExplanation:",
            'fix':     f"Fix the following {language} code.{(' Error: ' + extra) if extra else ''}\n\n```{language}\n{code}\n```\n\nFixed code:",
            'optimize':f"Optimize this {language} code for better performance and readability:\n\n```{language}\n{code}\n```\n\nOptimized code:",
            'format':  f"Format and clean up this {language} code following best practices:\n\n```{language}\n{code}\n```\n\nFormatted code:",
            'test':    f"Generate comprehensive unit tests for this {language} code:\n\n```{language}\n{code}\n```\n\nUnit tests:",
            'chat':    f"{'Code context:\n```' + language + '\n' + code + '\n```\n\n' if code.strip() else ''}User question: {extra}\n\nAnswer:",
        }

        temperatures = {
            'explain': 0.7, 'fix': 0.3, 'optimize': 0.5,
            'format': 0.2, 'test': 0.4, 'chat': 0.7,
        }

        prompt = prompts.get(action, f"Help with this {language} code:\n\n```{language}\n{code}\n```")
        temp   = temperatures.get(action, 0.7)
        max_t  = 256 if action == 'format' else 2048

        yield from provider.stream(prompt, max_tokens=max_t, temperature=temp)
    
    def _call_provider(self, action: str, code: str, extra: str = None, language: str = 'python') -> str:
        """Call provider with intelligent fallback - Groq first, then OpenRouter"""
        
        # Try Groq first (primary - ultra-fast)
        providers = [self.groq, self.openrouter]
        
        for provider in providers:
            if not provider:
                continue
            
            try:
                self._last_provider = provider.__class__.__name__.replace('AI', '').lower()
                
                if action == 'fix':
                    return provider.fix(code, extra, language=language)
                elif action == 'explain':
                    return provider.explain(code, language=language)
                elif action == 'optimize':
                    return provider.optimize(code, extra, language=language)
                elif action == 'generate':
                    return provider.generate(code)
                elif action == 'review':
                    return provider.review(code)
                elif action == 'suggest':
                    return provider.suggest(code, extra)
            
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} {action} failed: {e}")
                continue
        
        return None


# Singleton instance
_multi_ai = None


def get_multi_provider_ai() -> MultiProviderAI:
    """Get or create multi-provider AI instance"""
    global _multi_ai
    if _multi_ai is None:
        _multi_ai = MultiProviderAI()
    return _multi_ai
