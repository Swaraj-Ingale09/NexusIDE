"""
NexusIDE Router - Intelligent provider switching
Routes tasks to Groq (primary) with OpenRouter/NVIDIA fallbacks
"""

import os
import requests
import openai
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings
from typing import Dict, List, Tuple
import time
import logging

logger = logging.getLogger(__name__)

class AIRouter:
    """
    Routes AI tasks to optimal provider based on:
    - Task type (code completion, analysis, chat, formatting)
    - Speed (Groq first for ultra-fast inference)
    - Provider availability with fallback
    """
    
    def __init__(self):
        from apps.compiler.groq_key_pool import get_groq_pool
        self.groq_pool = get_groq_pool()
        self.groq_pool.load_from_env()
        self.openrouter_key = settings.OPENROUTER_API_KEY
        self.nvidia_nim_key = settings.NVIDIA_NIM_API_KEY
        
        # Groq client is now created per-request with pool keys
        self.groq_client = None
        
        # Task routing configuration - GROQ PRIMARY
        self.task_routing = {
            'code_completion': {
                'primary': 'groq',
                'fallback': 'openrouter',
                'timeout': 10,
                'model_groq': 'llama-3.3-70b-versatile',
                'model_openrouter': 'openrouter/auto',
                'model_nvidia': 'nvidia/nemotron-3-super-120b-a12b:free',
                'max_tokens': 300,
                'temperature': 0.2,
            },
            'code_analysis': {
                'primary': 'groq',
                'fallback': 'openrouter',
                'timeout': 15,
                'model_groq': 'llama-3.3-70b-versatile',
                'model_openrouter': 'openrouter/auto',
                'model_nvidia': 'nvidia/nemotron-3-super-120b-a12b:free',
                'max_tokens': 2000,
                'temperature': 0.4,
            },
            'bug_fix': {
                'primary': 'groq',
                'fallback': 'nvidia',
                'timeout': 15,
                'model_groq': 'llama-3.3-70b-versatile',
                'model_openrouter': 'nvidia/nemotron-3-ultra-550b-a55b:free',
                'model_nvidia': 'nvidia/nemotron-3-ultra-550b-a55b:free',
                'max_tokens': 2500,
                'temperature': 0.3,
            },
            'code_explanation': {
                'primary': 'groq',
                'fallback': 'nvidia',
                'timeout': 15,
                'model_groq': 'llama-3.3-70b-versatile',
                'model_openrouter': 'nvidia/nemotron-3-ultra-550b-a55b:free',
                'model_nvidia': 'nvidia/nemotron-3-ultra-550b-a55b:free',
                'max_tokens': 2000,
                'temperature': 0.5,
            },
            'chat': {
                'primary': 'groq',
                'fallback': 'openrouter',
                'timeout': 12,
                'model_groq': 'llama-3.3-70b-versatile',
                'model_openrouter': 'openrouter/auto',
                'model_nvidia': 'nvidia/nemotron-3-super-120b-a12b:free',
                'max_tokens': 1500,
                'temperature': 0.6,
            },
            'format_code': {
                'primary': 'groq',
                'fallback': 'openrouter',
                'timeout': 10,
                'model_groq': 'llama-3.3-70b-versatile',
                'model_openrouter': 'openrouter/auto',
                'model_nvidia': 'nvidia/nemotron-3-super-120b-a12b:free',
                'max_tokens': 1000,
                'temperature': 0.1,
            },
            'test_generation': {
                'primary': 'groq',
                'fallback': 'nvidia',
                'timeout': 15,
                'model_groq': 'llama-3.3-70b-versatile',
                'model_openrouter': 'qwen/qwen3-coder:free',
                'model_nvidia': 'nvidia/nemotron-3-ultra-550b-a55b:free',
                'max_tokens': 3000,
                'temperature': 0.4,
            }
        }
        
        # Provider status tracking
        self.provider_stats = {
            'groq': {'success': 0, 'failed': 0, 'avg_time': 0},
            'nvidia': {'success': 0, 'failed': 0, 'avg_time': 0},
            'openrouter': {'success': 0, 'failed': 0, 'avg_time': 0}
        }
    
    def get_routing_decision(self, task_type: str) -> Tuple[str, str]:
        """
        Determine which provider to use for a task
        Returns: (primary_provider, fallback_provider)
        """
        if task_type not in self.task_routing:
            # Default to OpenRouter for unknown tasks
            return ('openrouter', 'nvidia')
        
        config = self.task_routing[task_type]
        primary = config['primary']
        fallback = config['fallback']
        
        # Adjust based on provider health
        if self.provider_stats[primary]['failed'] > 5:
            # Switch primary if failing too much
            primary, fallback = fallback, primary
        
        return primary, fallback
    
    def call_groq(self, prompt: str, task_type: str, code_context: str = "") -> Dict:
        """Call Groq API via key pool with automatic rotation."""
        config = self.task_routing.get(task_type, self.task_routing['chat'])
        
        if not self.groq_pool.keys:
            return {'provider': 'groq', 'result': None, 'error': 'No Groq API keys', 'success': False}
        
        max_attempts = min(len(self.groq_pool.keys), 5)
        last_error = None
        
        for attempt in range(max_attempts):
            key_state = self.groq_pool.get_key()
            if not key_state:
                last_error = 'All Groq keys exhausted'
                break
            
            try:
                start_time = time.time()
                system_prompt = self._get_system_prompt(task_type)
                
                user_content = prompt
                if code_context:
                    user_content = f"Code:\n```python\n{code_context}\n```\n\n{prompt}"
                
                client = openai.OpenAI(
                    api_key=key_state.key,
                    base_url="https://api.groq.com/openai/v1"
                )
                response = client.chat.completions.create(
                    model=config['model_groq'],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=config['max_tokens'],
                    temperature=config['temperature'],
                    timeout=config['timeout'],
                )
                
                result = response.choices[0].message.content
                elapsed = time.time() - start_time
                tokens_used = getattr(response.usage, 'total_tokens', 0) if response.usage else 0
                
                self.groq_pool.record_success(key_state, tokens_used)
                self.provider_stats['groq']['success'] += 1
                self._update_avg_time('groq', elapsed)
                
                logger.info("Groq responded in %.2fs for %s (key: %s)", elapsed, task_type, key_state.name)
                
                return {
                    'provider': 'groq',
                    'result': result,
                    'error': None,
                    'success': True,
                    'response_time': elapsed,
                    'model': config['model_groq'],
                }
                
            except Exception as e:
                elapsed = time.time() - start_time if 'start_time' in dir() else 0
                last_error = str(e)
                self.groq_pool.record_failure(key_state, last_error)
                self.provider_stats['groq']['failed'] += 1
                logger.warning("Groq key '%s' failed (attempt %d/%d): %s",
                             key_state.name, attempt + 1, max_attempts, last_error[:100])
                continue
        
        return {
            'provider': 'groq',
            'result': None,
            'error': f'All {max_attempts} attempts failed: {last_error}',
            'success': False,
            'response_time': 0,
        }
    
    def call_nvidia_nim(self, prompt: str, task_type: str, code_context: str = "") -> Dict:
        """
        Call NVIDIA NIM API using requests library (OpenAI-compatible endpoint)
        """
        config = self.task_routing.get(task_type, self.task_routing['chat'])
        
        try:
            start_time = time.time()
            
            # Build context-aware prompt
            system_prompt = self._get_system_prompt(task_type)
            full_prompt = f"{prompt}"
            
            if code_context:
                full_prompt = f"Code to analyze:\n```python\n{code_context}\n```\n\n{prompt}"
            
            headers = {
                "Authorization": f"Bearer {self.nvidia_nim_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": config['model_nvidia'],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": config['temperature'],
                "max_tokens": config['max_tokens'],
                "top_p": 0.9
            }
            if config.get('reasoning_enabled'):
                payload["reasoning"] = {"enabled": True}
            
            # Call NVIDIA NIM OpenAI-compatible endpoint
            response = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=config['timeout']
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                result = data['choices'][0]['message']['content']
                
                # Update stats
                self.provider_stats['nvidia']['success'] += 1
                self._update_avg_time('nvidia', elapsed_time)
                
                logger.info(f"NVIDIA NIM success for {task_type} in {elapsed_time:.2f}s")
                
                return {
                    'provider': 'nvidia',
                    'result': result,
                    'time': elapsed_time,
                    'success': True
                }
            else:
                self.provider_stats['nvidia']['failed'] += 1
                error_msg = f"NVIDIA NIM error ({response.status_code}): {response.text[:100]}"
                logger.warning(error_msg)
                return {
                    'provider': 'nvidia',
                    'result': None,
                    'error': error_msg,
                    'success': False
                }
        
        except Exception as e:
            self.provider_stats['nvidia']['failed'] += 1
            error_msg = f"NVIDIA NIM exception: {str(e)[:100]}"
            logger.error(error_msg)
            return {
                'provider': 'nvidia',
                'result': None,
                'error': error_msg,
                'success': False
            }
    
    def call_openrouter(self, prompt: str, task_type: str, code_context: str = "") -> Dict:
        """
        Call OpenRouter API with free tier Nemotron model
        """
        config = self.task_routing.get(task_type, self.task_routing['chat'])
        
        try:
            start_time = time.time()
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "HTTP-Referer": "https://nexusIDE.dev",
                "X-Title": "NexusIDE",
                "Content-Type": "application/json"
            }
            
            # Build context-aware prompt
            system_prompt = self._get_system_prompt(task_type)
            full_prompt = f"{prompt}"
            
            if code_context:
                full_prompt = f"Code to analyze:\n```python\n{code_context}\n```\n\n{prompt}"
            
            payload = {
                "model": config['model_openrouter'],
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": config['temperature'],
                "max_tokens": config['max_tokens'],
                "top_p": 0.9
            }
            if config.get('reasoning_enabled'):
                payload["reasoning"] = {"enabled": True}
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=config['timeout']
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                result = data['choices'][0]['message']['content']
                
                # Update stats
                self.provider_stats['openrouter']['success'] += 1
                self._update_avg_time('openrouter', elapsed_time)
                
                logger.info(f"OpenRouter success for {task_type} in {elapsed_time:.2f}s")
                
                return {
                    'provider': 'openrouter',
                    'result': result,
                    'time': elapsed_time,
                    'success': True
                }
            else:
                self.provider_stats['openrouter']['failed'] += 1
                error_msg = f"OpenRouter error ({response.status_code}): {response.text}"
                logger.warning(error_msg)
                return {
                    'provider': 'openrouter',
                    'result': None,
                    'error': error_msg,
                    'success': False
                }
        
        except Exception as e:
            self.provider_stats['openrouter']['failed'] += 1
            error_msg = f"OpenRouter exception: {str(e)}"
            logger.error(error_msg)
            return {
                'provider': 'openrouter',
                'result': None,
                'error': error_msg,
                'success': False
            }
    
    def route_task(self, task_type: str, prompt: str, code_context: str = "") -> Dict:
        """
        Intelligently route task to best provider.
        Tries Groq first (ultra-fast), then falls back to OpenRouter/NVIDIA.
        """
        config = self.task_routing.get(task_type, self.task_routing['chat'])
        
        # Try Groq first (primary for all tasks)
        if config['primary'] == 'groq' and self.groq_pool.keys:
            result = self.call_groq(prompt, task_type, code_context)
            if result['success']:
                return result
        
        # Fallback to OpenRouter or NVIDIA
        fallback = config['fallback']
        if fallback == 'nvidia':
            result = self.call_nvidia_nim(prompt, task_type, code_context)
        else:
            result = self.call_openrouter(prompt, task_type, code_context)
        
        # If fallback also failed, try the third provider
        if not result['success']:
            third = 'openrouter' if fallback == 'nvidia' else 'nvidia'
            if third == 'openrouter':
                result = self.call_openrouter(prompt, task_type, code_context)
            else:
                result = self.call_nvidia_nim(prompt, task_type, code_context)
        
        return result
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get context-aware system prompt"""
        prompts = {
            'code_completion': "You are a Python code completion expert. Complete the code concisely and accurately. Return only the completion without explanation.",
            'code_analysis': "You are a Python code analyzer. Analyze the code for bugs, performance issues, and best practices. Provide detailed, structured feedback.",
            'bug_fix': "You are an expert Python debugger. Identify bugs in the code and provide fixed versions with clear explanations.",
            'code_explanation': "You are a Python expert educator. Explain the code clearly and thoroughly, making it understandable.",
            'chat': "You are a helpful Python coding assistant. Answer questions and provide practical coding advice.",
            'format_code': "You are a Python code formatter. Format the code according to PEP 8 standards. Return only the formatted code.",
            'test_generation': "You are a Python testing expert. Generate comprehensive, well-structured unit tests for the provided code.",
        }
        return prompts.get(task_type, "You are a helpful Python coding assistant.")
    
    def _update_avg_time(self, provider: str, elapsed_time: float):
        """Update average response time"""
        stats = self.provider_stats[provider]
        total_success = stats['success']
        current_avg = stats['avg_time']
        stats['avg_time'] = (current_avg * (total_success - 1) + elapsed_time) / total_success
    
    def get_provider_stats(self) -> Dict:
        """Get provider statistics"""
        return {
            'nvidia': {
                **self.provider_stats['nvidia'],
                'success_rate': (
                    self.provider_stats['nvidia']['success'] / 
                    (self.provider_stats['nvidia']['success'] + self.provider_stats['nvidia']['failed'] or 1)
                ) * 100
            },
            'openrouter': {
                **self.provider_stats['openrouter'],
                'success_rate': (
                    self.provider_stats['openrouter']['success'] / 
                    (self.provider_stats['openrouter']['success'] + self.provider_stats['openrouter']['failed'] or 1)
                ) * 100
            }
        }


# Global instance
ai_router = AIRouter()
