"""
Multi-Provider AI Integration for NexusIDE
Supports: DeepSeek R1, Qwen3, OpenAI, Claude, OpenRouter, NVIDIA NIM
Each provider has optimized prompts and configurations for their strengths.
"""

import os
import json
import requests
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from abc import ABC, abstractmethod
import anthropic
import openai

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""
    DEEPSEEK_R1 = "deepseek_r1"
    QWEN3 = "qwen3"
    OPENAI = "openai"
    CLAUDE = "claude"
    OPENROUTER = "openrouter"
    NVIDIA_NIM = "nvidia_nim"
    GROQ = "groq"


class BaseAIProvider(ABC):
    """Abstract base class for all AI providers"""
    
    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.timeout = kwargs.get('timeout', 30)
        self.max_tokens = kwargs.get('max_tokens', 2048)
        self.temperature = kwargs.get('temperature', 0.7)
    
    @abstractmethod
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Make API call and return response"""
        pass
    
    @abstractmethod
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream API response"""
        pass


class DeepSeekR1Provider(BaseAIProvider):
    """
    DeepSeek R1 - Excellent for debugging and reasoning
    Best for: Bug diagnosis, complex problem solving, code analysis
    Endpoint: https://api.deepseek.com/v1
    """
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key,
            model=kwargs.get('model', 'deepseek-reasoner'),
            **kwargs
        )
        self.base_url = "https://api.deepseek.com/v1"
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Call DeepSeek R1 API"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek R1 API error: {e}")
            raise
    
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream DeepSeek R1 response"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            with self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                timeout=self.timeout,
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"DeepSeek R1 streaming error: {e}")
            raise


class Qwen3Provider(BaseAIProvider):
    """
    Qwen3 (Alibaba) - Strong for coding tasks
    Best for: Code generation, quick refactoring, chat
    Endpoint: https://dashscope.aliyuncs.com/compatible-mode/v1
    """
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key,
            model=kwargs.get('model', 'qwen-max-latest'),  # or qwen-plus, qwen-turbo
            **kwargs
        )
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Call Qwen3 API"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Qwen3 API error: {e}")
            raise
    
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream Qwen3 response"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            with self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                timeout=self.timeout,
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Qwen3 streaming error: {e}")
            raise


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT models"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key,
            model=kwargs.get('model', 'gpt-4o-mini'),
            **kwargs
        )
        self.client = openai.OpenAI(api_key=api_key)
    
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Call OpenAI API"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream OpenAI response"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            with self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                timeout=self.timeout,
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude models"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key,
            model=kwargs.get('model', 'claude-3-5-sonnet-20241022'),
            **kwargs
        )
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Call Claude API"""
        try:
            response = self.client.messages.create(
                model=self.model,
                messages=messages,
                system=system_prompt or "You are an expert programmer.",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream Claude response"""
        try:
            with self.client.messages.stream(
                model=self.model,
                messages=messages,
                system=system_prompt or "You are an expert programmer.",
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            raise


class OpenRouterProvider(BaseAIProvider):
    """OpenRouter - Universal AI gateway"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key,
            model=kwargs.get('model', 'openrouter/auto'),
            **kwargs
        )
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Call OpenRouter API"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise
    
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream OpenRouter response"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            with self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                timeout=self.timeout,
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenRouter streaming error: {e}")
            raise


class NVIDIANIMProvider(BaseAIProvider):
    """NVIDIA NIM - Local or cloud inference"""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(
            api_key,
            model=kwargs.get('model', 'nvidia/nemotron-3-super-120b-a12b'),
            **kwargs
        )
        self.base_url = os.environ.get('NVIDIA_NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1')
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Call NVIDIA NIM API"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"NVIDIA NIM API error: {e}")
            raise
    
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream NVIDIA NIM response"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            with self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                timeout=self.timeout,
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"NVIDIA NIM streaming error: {e}")
            raise


class GroqProvider(BaseAIProvider):
    """
    Groq - Ultra-fast inference via LPU
    Best for: Low-latency code generation, explanations, fixes
    Model: llama-3.3-70b-versatile (128K context, strong at code)
    Endpoint: https://api.groq.com/openai/v1
    """
    
    def __init__(self, api_key: str, model: str = None, **kwargs):
        super().__init__(
            api_key,
            model=model or 'llama-3.3-70b-versatile',
            **kwargs
        )
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    def call(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Call Groq API"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise
    
    def stream_call(self, messages: List[Dict[str, str]], system_prompt: str = None):
        """Stream Groq response"""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            with self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                timeout=self.timeout,
            ) as stream:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            raise


class ProviderFactory:
    """Factory for creating provider instances"""
    
    _providers = {
        AIProvider.DEEPSEEK_R1: DeepSeekR1Provider,
        AIProvider.QWEN3: Qwen3Provider,
        AIProvider.OPENAI: OpenAIProvider,
        AIProvider.CLAUDE: ClaudeProvider,
        AIProvider.OPENROUTER: OpenRouterProvider,
        AIProvider.NVIDIA_NIM: NVIDIANIMProvider,
        AIProvider.GROQ: GroqProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> BaseAIProvider:
        """Create a provider instance"""
        
        # Normalize provider name
        provider_name = provider_name.lower().strip()
        
        # Try enum lookup first
        try:
            provider_enum = AIProvider[provider_name.upper()]
        except KeyError:
            # Try value lookup
            for enum_member in AIProvider:
                if enum_member.value == provider_name:
                    provider_enum = enum_member
                    break
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = cls._providers.get(provider_enum)
        if not provider_class:
            raise ValueError(f"No implementation for provider: {provider_name}")
        
        # Get API key and model from kwargs or environment
        api_key = kwargs.get('api_key')
        model = kwargs.get('model')
        
        if not api_key:
            env_key = f"{provider_enum.value.upper()}_API_KEY"
            api_key = os.environ.get(env_key)
        
        if not api_key:
            raise ValueError(f"API key not provided for {provider_name}")
        
        return provider_class(api_key, model=model, **kwargs)
