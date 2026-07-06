"""
Unified AI Service for NexusIDE
Integrates multi-provider routing, RAG, and task classification
Main entry point for all AI operations
"""

import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

from django.core.cache import cache

from apps.compiler.ai_multi_provider import ProviderFactory, AIProvider
from apps.compiler.ai_task_router import TaskRouter, TaskType, ContextAnalyzer
from apps.compiler.ai_rag_retriever import ProjectContextRetriever, CodeSnippetFinder
from apps.compiler.ai_config import (
    get_primary_model_for_task, MODEL_CONFIGS, SYSTEM_PROMPTS,
    TASK_MODEL_PREFERENCES, LOGGING_CONFIG
)

logger = logging.getLogger(__name__)


class AIService:
    """
    Unified AI service with smart routing, RAG, and multi-provider support
    
    Usage:
        service = AIService()
        
        # Simple request (auto-routes)
        result = service.process_request(
            user_input="Fix this bug",
            code=buggy_code,
            error=error_message
        )
        
        # With context retrieval
        result = service.process_request(
            user_input="Fix this bug",
            code=buggy_code,
            error=error_message,
            current_file="/path/to/file.py",
            enable_rag=True
        )
        
        # Streaming response
        for chunk in service.stream_response(...):
            print(chunk, end='')
    """
    
    def __init__(self):
        self.router = TaskRouter()
        self.context_retriever = ProjectContextRetriever()
        self.snippet_finder = CodeSnippetFinder()
        self.provider_factory = ProviderFactory()
        self.call_history = []
    
    def process_request(self,
                       user_input: str,
                       code: str = None,
                       error: str = None,
                       language: str = 'python',
                       current_file: str = None,
                       enable_rag: bool = True,
                       preferred_provider: str = None) -> Dict:
        """
        Process AI request with intelligent routing and RAG
        """
        
        # Check cache first (skip caching for code fixes/changes)
        cache_key = None
        skip_cache = any(kw in user_input.lower() for kw in ['fix', 'change', 'modify', 'refactor', 'write'])
        if not skip_cache:
            cache_input = f"{user_input}:{code}:{error}:{language}"
            cache_key = f"ai:resp:{hashlib.md5(cache_input.encode()).hexdigest()}"
            cached = cache.get(cache_key)
            if cached:
                logger.info("Returning cached AI response")
                return cached
        
        try:
            # Step 1: Route request to determine best model
            routing = self.router.route_request(user_input, code, error)
            task_type = routing['task_type']
            primary_provider = preferred_provider or routing['primary_provider']
            
            logger.info(f"Routing: {task_type} -> {primary_provider}")
            
            # Step 2: Build context (optional RAG)
            context = ""
            project_context_included = False
            
            if enable_rag and current_file:
                rag_context = self.context_retriever.get_context(
                    current_file=current_file,
                    error_message=error,
                    search_terms=self._extract_search_terms(user_input)
                )
                context = self._format_rag_context(rag_context)
                project_context_included = True
            
            # Step 3: Build prompt
            system_prompt = self._get_system_prompt(task_type)
            user_message = self._build_user_message(user_input, code, error, context, language)
            
            # Step 4: Select and call provider
            provider = self.provider_factory.create_provider(primary_provider)
            
            messages = [{"role": "user", "content": user_message}]
            response = provider.call(messages, system_prompt)
            
            # Step 5: Log and return
            result = {
                'response': response,
                'task_type': task_type,
                'provider_used': primary_provider,
                'confidence': routing.get('task_confidence', 0.5),
                'tokens_used': {'estimated': len(response) // 4},
                'reasoning': routing.get('reasoning', ''),
                'project_context_included': project_context_included,
            }
            
            # Record in history
            self.call_history.append({
                'user_input': user_input[:100],
                'task_type': task_type,
                'provider': primary_provider,
                'success': True,
            })
            
            # Cache non-mutating responses for 1 hour
            if cache_key and not skip_cache:
                cache.set(cache_key, result, 3600)
            
            return result
        
        except Exception as e:
            logger.error(f"AI Service error: {e}")
            
            # Try fallback provider
            try:
                fallback = routing.get('fallback_provider', 'openai')
                logger.warning(f"Falling back to {fallback}")
                
                provider = self.provider_factory.create_provider(fallback)
                messages = [{"role": "user", "content": user_input}]
                response = provider.call(messages)
                
                return {
                    'response': response,
                    'task_type': routing.get('task_type', 'unknown'),
                    'provider_used': fallback,
                    'confidence': 0.3,
                    'error': str(e),
                }
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return {
                    'response': f"Error: Could not process request ({str(e)})",
                    'error': str(e2),
                    'provider_used': 'none',
                }
    
    def stream_response(self,
                       user_input: str,
                       code: str = None,
                       error: str = None,
                       language: str = 'python',
                       current_file: str = None,
                       preferred_provider: str = None):
        """Stream AI response for real-time display"""
        
        try:
            # Route and get provider
            routing = self.router.route_request(user_input, code, error)
            primary_provider = preferred_provider or routing['primary_provider']
            
            # Get system prompt
            system_prompt = self._get_system_prompt(routing['task_type'])
            
            # Build user message
            context = ""
            if current_file:
                rag_context = self.context_retriever.get_context(
                    current_file=current_file,
                    error_message=error,
                    search_terms=self._extract_search_terms(user_input)
                )
                context = self._format_rag_context(rag_context)
            
            user_message = self._build_user_message(user_input, code, error, context, language)
            
            # Stream response
            provider = self.provider_factory.create_provider(primary_provider)
            messages = [{"role": "user", "content": user_message}]
            
            for chunk in provider.stream_call(messages, system_prompt):
                yield chunk
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"\nError: {str(e)}"
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get appropriate system prompt for task type"""
        
        # Map TaskType to prompt key
        prompt_map = {
            'bug_diagnosis': 'debug',
            'code_review': 'review',
            'optimization': 'optimize',
            'auto_fix': 'debug',
            'code_generation': 'generate',
            'explanation': 'explain',
            'refactoring': 'refactor',
            'formatting': 'generate',
            'documentation': 'explain',
            'testing': 'generate',
        }
        
        prompt_key = prompt_map.get(task_type, 'generate')
        return SYSTEM_PROMPTS.get(prompt_key, SYSTEM_PROMPTS['generate'])
    
    def _build_user_message(self, user_input: str, code: str = None,
                           error: str = None, context: str = None,
                           language: str = 'python') -> str:
        """Build comprehensive user message with all context"""
        
        parts = []
        
        # Project context (if RAG was used)
        if context:
            parts.append(context)
        
        # Error context
        if error:
            parts.append(f"\nERROR/ISSUE:\n{error}")
        
        # Code context
        if code:
            lang_block = language.lower() if language else 'python'
            parts.append(f"\nCODE ({language}):\n```{lang_block}\n{code}\n```")
        
        # User request
        parts.append(f"\nREQUEST:\n{user_input}")
        
        return "\n".join(parts)
    
    def _format_rag_context(self, rag_data: Dict) -> str:
        """Format RAG context into readable string"""
        
        parts = []
        
        if rag_data.get('project_overview'):
            parts.append(f"PROJECT CONTEXT:\n{rag_data['project_overview']}")
        
        if rag_data.get('dependencies'):
            parts.append(f"\nDEPENDENCIES:\n{', '.join(rag_data['dependencies'][:10])}")
        
        if rag_data.get('file_contents'):
            parts.append(f"\nRELATED FILES:")
            for filepath, content in rag_data['file_contents'].items():
                parts.append(f"\n{content}")
        
        return "\n".join(parts)
    
    def _extract_search_terms(self, user_input: str) -> List[str]:
        """Extract search terms from user input"""
        
        # Simple extraction: common nouns from input
        stop_words = {'a', 'an', 'the', 'is', 'are', 'be', 'been', 'being',
                     'have', 'has', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'can', 'this', 'that'}
        
        words = user_input.lower().split()
        terms = [w for w in words if len(w) > 3 and w not in stop_words]
        
        return terms[:5]


class AIAssistant:
    """
    High-level AI assistant for common coding tasks
    Wrapper around AIService with convenient methods
    """
    
    def __init__(self):
        self.service = AIService()
    
    def debug_code(self, code: str, error: str, language: str = 'python',
                  current_file: str = None) -> str:
        """Debug code with error message"""
        
        result = self.service.process_request(
            user_input="Debug and fix this code",
            code=code,
            error=error,
            language=language,
            current_file=current_file,
            enable_rag=True
        )
        
        return result['response']
    
    def review_code(self, code: str, focus: str = None, language: str = 'python') -> str:
        """Review code for quality and issues"""
        
        user_input = "Review this code"
        if focus:
            user_input += f" focusing on {focus}"
        
        result = self.service.process_request(
            user_input=user_input,
            code=code,
            language=language,
            enable_rag=False
        )
        
        return result['response']
    
    def optimize_code(self, code: str, goal: str = 'speed', language: str = 'python') -> str:
        """Optimize code for speed, memory, readability, etc."""
        
        result = self.service.process_request(
            user_input=f"Optimize this code for {goal}",
            code=code,
            language=language,
            enable_rag=False
        )
        
        return result['response']
    
    def generate_code(self, description: str, language: str = 'python') -> str:
        """Generate code from description"""
        
        result = self.service.process_request(
            user_input=f"Write {language} code to: {description}",
            language=language,
            enable_rag=False
        )
        
        return result['response']
    
    def explain_code(self, code: str, language: str = 'python') -> str:
        """Explain what code does"""
        
        result = self.service.process_request(
            user_input="Explain what this code does step by step",
            code=code,
            language=language,
            enable_rag=False
        )
        
        return result['response']
