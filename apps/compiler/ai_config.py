"""
AI Model Configuration for NexusIDE
Settings for multi-provider AI integration with DeepSeek R1 and Qwen3
"""

import os
from typing import Dict, List, Tuple

# API Keys (from environment variables)
DEEPSEEK_R1_API_KEY = os.environ.get('DEEPSEEK_R1_API_KEY', '')
QWEN3_API_KEY = os.environ.get('QWEN3_API_KEY', '')

# Existing providers (keep backward compatibility)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
NVIDIA_NIM_API_KEY = os.environ.get('NVIDIA_NIM_API_KEY', '')
NVIDIA_NIM_BASE_URL = os.environ.get('NVIDIA_NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1')

# Groq (ultra-fast inference)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# Model configurations
MODEL_CONFIGS = {
    'deepseek_r1': {
        'name': 'DeepSeek R1',
        'model': 'deepseek-reasoner',
        'api_key_env': 'DEEPSEEK_R1_API_KEY',
        'endpoint': 'https://api.deepseek.com/v1',
        'timeout': 25,
        'best_for': ['debugging', 'reasoning', 'analysis'],
        'max_tokens': 4000,
        'default_temperature': 0.2,
    },
    'qwen3': {
        'name': 'Qwen3 (Alibaba)',
        'model': 'qwen-max-latest',
        'api_key_env': 'QWEN3_API_KEY',
        'endpoint': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'timeout': 20,
        'best_for': ['coding', 'generation', 'refactoring'],
        'max_tokens': 2048,
        'default_temperature': 0.3,
    },
    'openai': {
        'name': 'OpenAI',
        'model': OPENAI_MODEL,
        'api_key_env': 'OPENAI_API_KEY',
        'endpoint': 'https://api.openai.com/v1',
        'timeout': 20,
        'best_for': ['chat', 'analysis', 'generation'],
        'max_tokens': 2048,
        'default_temperature': 0.3,
    },
    'claude': {
        'name': 'Claude (Anthropic)',
        'model': ANTHROPIC_MODEL,
        'api_key_env': 'ANTHROPIC_API_KEY',
        'endpoint': 'https://api.anthropic.com',
        'timeout': 20,
        'best_for': ['analysis', 'writing', 'reasoning'],
        'max_tokens': 2048,
        'default_temperature': 0.3,
    },
    'openrouter': {
        'name': 'OpenRouter',
        'model': 'openrouter/auto',
        'api_key_env': 'OPENROUTER_API_KEY',
        'endpoint': 'https://openrouter.ai/api/v1',
        'timeout': 20,
        'best_for': ['any'],
        'max_tokens': 2048,
        'default_temperature': 0.3,
    },
    'nvidia_nim': {
        'name': 'NVIDIA NIM',
        'model': 'nvidia/nemotron-3-super-120b-a12b',
        'api_key_env': 'NVIDIA_NIM_API_KEY',
        'endpoint': NVIDIA_NIM_BASE_URL,
        'timeout': 20,
        'best_for': ['coding', 'analysis'],
        'max_tokens': 2048,
        'default_temperature': 0.3,
    },
    'groq': {
        'name': 'Groq (Llama 3.3 70B)',
        'model': 'llama-3.3-70b-versatile',
        'api_key_env': 'GROQ_API_KEY',
        'endpoint': 'https://api.groq.com/openai/v1',
        'timeout': 15,
        'best_for': ['coding', 'explanation', 'fix', 'chat', 'analysis'],
        'max_tokens': 4096,
        'default_temperature': 0.3,
    },
}

# Enable/disable providers
ENABLED_PROVIDERS = [
    'groq',          # PRIMARY: Ultra-fast inference, best for all code tasks
    'deepseek_r1',   # FALLBACK: Reasoning & debugging
    'qwen3',         # FALLBACK: Code generation
    'openrouter',    # FALLBACK: Universal gateway
]

# Task-specific model preferences (Groq first for speed, fallbacks for depth)
TASK_MODEL_PREFERENCES = {
    'bug_diagnosis': ['groq', 'deepseek_r1', 'qwen3'],
    'code_review': ['groq', 'deepseek_r1', 'qwen3'],
    'optimization': ['groq', 'deepseek_r1', 'qwen3'],
    'auto_fix': ['groq', 'qwen3', 'deepseek_r1'],
    'code_generation': ['groq', 'qwen3', 'openai'],
    'refactoring': ['groq', 'qwen3', 'deepseek_r1'],
    'explanation': ['groq', 'qwen3', 'openai'],
    'formatting': ['groq', 'qwen3'],
    'testing': ['groq', 'qwen3', 'deepseek_r1'],
    'chat': ['groq', 'qwen3', 'openai'],
}

# RAG Configuration
RAG_CONFIG = {
    'enabled': True,
    'max_context_tokens': 4000,
    'max_files_to_include': 5,
    'relevant_extensions': {
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs',
        '.txt', '.md', '.json', '.yaml', '.yml', '.toml', '.xml'
    },
    'key_files': [
        'README.md',
        'requirements.txt',
        'package.json',
        'setup.py',
        '.env.example',
        'docker-compose.yml',
        'Dockerfile',
    ],
    'ignored_dirs': {
        '.git', '__pycache__', '.env', 'node_modules', '.venv', 'venv',
        'dist', 'build', '.pytest_cache', '.mypy_cache'
    }
}

# System prompts for different task types
SYSTEM_PROMPTS = {
    'debug': """You are an expert debugger. When analyzing code with errors:
1. Identify the root cause
2. Explain the error clearly
3. Provide a fix with minimal changes
4. Suggest how to prevent this in future
Be concise but thorough.""",
    
    'review': """You are a senior code reviewer. When reviewing code:
1. Check for bugs and edge cases
2. Assess code quality and style
3. Suggest improvements
4. Highlight security issues
Be constructive and specific.""",
    
    'optimize': """You are a performance optimization expert. When optimizing code:
1. Analyze time and space complexity
2. Identify bottlenecks
3. Suggest specific improvements
4. Provide optimized code with comments
Focus on practical improvements.""",
    
    'generate': """You are an expert software engineer. When generating code:
1. Write clean, idiomatic code
2. Follow language best practices
3. Add helpful comments
4. Handle edge cases
Generate complete, working code.""",
    
    'explain': """You are a patient code educator. When explaining code:
1. Break down the logic step by step
2. Explain the purpose and approach
3. Give analogies for complex concepts
4. Mention best practices
Make it understandable for all levels.""",
    
    'refactor': """You are a code refactoring expert. When refactoring code:
1. Preserve original functionality
2. Improve readability and maintainability
3. Reduce complexity
4. Apply modern patterns
Provide clear before/after explanation.""",
}

# Logging configuration
LOGGING_CONFIG = {
    'log_api_calls': True,
    'log_token_usage': True,
    'log_model_selection': True,
    'log_level': 'INFO',
}

# Performance settings
PERFORMANCE_CONFIG = {
    'cache_responses': True,
    'cache_ttl_seconds': 3600,
    'timeout_seconds': 30,
    'retry_attempts': 2,
    'retry_delay_seconds': 1,
}

# Cost tracking (if needed)
COST_TRACKING = {
    'enabled': False,
    'deepseek_r1': {
        'input_cost_per_1k_tokens': 0.55 / 1000,   # ¥ per token
        'output_cost_per_1k_tokens': 2.19 / 1000,
    },
    'qwen3': {
        'input_cost_per_1k_tokens': 0.4 / 1000,    # ¥ per token
        'output_cost_per_1k_tokens': 1.2 / 1000,
    },
}

def get_primary_model_for_task(task_type: str) -> str:
    """Get primary model recommendation for task type"""
    preferences = TASK_MODEL_PREFERENCES.get(task_type, ['qwen3', 'openai'])
    
    # Return first available enabled provider
    for model in preferences:
        if model in ENABLED_PROVIDERS:
            # Check if API key is available
            config = MODEL_CONFIGS.get(model)
            if config:
                api_key_env = config['api_key_env']
                if os.environ.get(api_key_env):
                    return model
    
    # Fallback to first enabled provider
    if ENABLED_PROVIDERS:
        return ENABLED_PROVIDERS[0]
    
    return 'openai'  # Ultimate fallback


def get_available_providers() -> Dict[str, str]:
    """Get list of available providers with their names"""
    available = {}
    
    for provider in ENABLED_PROVIDERS:
        config = MODEL_CONFIGS.get(provider)
        if config:
            api_key_env = config['api_key_env']
            if os.environ.get(api_key_env):
                available[provider] = config['name']
    
    return available


def validate_configuration() -> Tuple[bool, List[str]]:
    """Validate that configuration is correct"""

    issues = []
    
    # Check at least one provider has API key
    if not get_available_providers():
        issues.append("No API keys configured for any provider")
    
    # Check for deprecated settings
    if not os.environ.get('DEEPSEEK_R1_API_KEY'):
        issues.append("DeepSeek R1 API key not configured (DEEPSEEK_R1_API_KEY)")
    
    if not os.environ.get('QWEN3_API_KEY'):
        issues.append("Qwen3 API key not configured (QWEN3_API_KEY)")
    
    return len(issues) == 0, issues


# Test configuration on import
if __name__ == '__main__':
    valid, issues = validate_configuration()
    if valid:
        print("[OK] AI configuration is valid")
        print(f"Available providers: {list(get_available_providers().keys())}")
    else:
        print("✗ Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
