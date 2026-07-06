"""
Smart Task Router for NexusIDE
Classifies user requests and routes to optimal AI model
Uses task type + context to select best provider
"""

import re
import json
import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Classification of user tasks"""
    # High-complexity tasks (need reasoning)
    BUG_DIAGNOSIS = "bug_diagnosis"      # DeepSeek R1 (needs reasoning)
    CODE_REVIEW = "code_review"          # DeepSeek R1 (needs analysis)
    OPTIMIZATION = "optimization"        # DeepSeek R1 (needs reasoning)
    ARCHITECTURE = "architecture"        # DeepSeek R1 (needs reasoning)
    
    # Code generation tasks
    CODE_GENERATION = "code_generation"  # Qwen3 (fast, good generation)
    AUTO_FIX = "auto_fix"               # Qwen3 (can fix quickly)
    COMPLETION = "completion"            # Qwen3 (fast)
    REFACTORING = "refactoring"         # Qwen3 (good at refactoring)
    
    # Simple tasks
    EXPLANATION = "explanation"          # Any model (can use cheaper)
    FORMATTING = "formatting"            # Any model (simple task)
    DOCUMENTATION = "documentation"      # Qwen3 (good writing)
    TESTING = "testing"                 # Qwen3 (test generation)
    
    # Chat
    CHAT = "chat"                        # Qwen3 (conversational)
    GENERAL_HELP = "general_help"        # Qwen3 (chat)


class TaskRouter:
    """
    Smart router that:
    1. Analyzes user request
    2. Classifies task type
    3. Selects optimal provider
    4. Suggests model configuration
    """
    
    # Task classification patterns
    TASK_PATTERNS = {
        TaskType.BUG_DIAGNOSIS: [
            r'(bug|error|issue|problem|crash|failed|exception|traceback)',
            r'(why|how does this|what\'s wrong|how can i fix|help me debug)',
            r'(error message|stack trace|exception)',
        ],
        TaskType.CODE_REVIEW: [
            r'(review|analyze|check|audit|evaluate)',
            r'(code quality|best practice|improvement|refactor)',
            r'(security|performance|edge case)',
        ],
        TaskType.OPTIMIZATION: [
            r'(optimize|faster|slower|speed|memory|efficiency)',
            r'(improve|performance|big o|complexity)',
            r'(scale|bottleneck|slow)',
        ],
        TaskType.AUTO_FIX: [
            r'(fix|correct|repair|resolve)',
            r'(code|error|bug|issue)',
            r'(make it work|broken|not working)',
        ],
        TaskType.CODE_GENERATION: [
            r'(write|generate|create|implement|build)',
            r'(code|function|method|script|program)',
            r'(that|which|to)',
        ],
        TaskType.REFACTORING: [
            r'(refactor|rewrite|improve|clean|simplify)',
            r'(code|function|logic|structure)',
            r'(better|cleaner|more readable)',
        ],
        TaskType.FORMATTING: [
            r'(format|indent|style|lint)',
            r'(code|python|javascript|etc)',
        ],
        TaskType.EXPLANATION: [
            r'(explain|understand|how does|what does|help me understand)',
            r'(code|this|logic|function)',
            r'(do|work|mean)',
        ],
        TaskType.DOCUMENTATION: [
            r'(document|docstring|comment|add docs)',
            r'(function|code|class|method)',
        ],
        TaskType.TESTING: [
            r'(test|unit test|test case|test generation)',
            r'(for|to test|verify)',
        ],
        TaskType.CHAT: [
            r'(hello|hi|thanks|okay|cool|nice)',
            r'(how are you|what can you|tell me)',
        ],
    }
    
    # Provider recommendations for task types (Groq primary for speed)
    PROVIDER_RECOMMENDATIONS = {
        TaskType.BUG_DIAGNOSIS: {
            'primary': 'groq',             # Fast + strong reasoning
            'fallback': 'deepseek_r1',
            'temperature': 0.3,
            'max_tokens': 3000,
        },
        TaskType.CODE_REVIEW: {
            'primary': 'groq',             # Fast analysis
            'fallback': 'deepseek_r1',
            'temperature': 0.4,
            'max_tokens': 2500,
        },
        TaskType.OPTIMIZATION: {
            'primary': 'groq',             # Fast reasoning
            'fallback': 'deepseek_r1',
            'temperature': 0.3,
            'max_tokens': 2500,
        },
        TaskType.ARCHITECTURE: {
            'primary': 'groq',             # Fast + 128K context
            'fallback': 'deepseek_r1',
            'temperature': 0.4,
            'max_tokens': 3000,
        },
        TaskType.CODE_GENERATION: {
            'primary': 'groq',             # Ultra-fast generation
            'fallback': 'qwen3',
            'temperature': 0.4,
            'max_tokens': 2000,
        },
        TaskType.AUTO_FIX: {
            'primary': 'groq',             # Ultra-fast fixes
            'fallback': 'qwen3',
            'temperature': 0.3,
            'max_tokens': 2000,
        },
        TaskType.COMPLETION: {
            'primary': 'groq',             # Ultra-fast
            'fallback': 'qwen3',
            'temperature': 0.3,
            'max_tokens': 500,
        },
        TaskType.REFACTORING: {
            'primary': 'groq',             # Fast refactoring
            'fallback': 'qwen3',
            'temperature': 0.4,
            'max_tokens': 2000,
        },
        TaskType.EXPLANATION: {
            'primary': 'groq',             # Fast explanations
            'fallback': 'qwen3',
            'temperature': 0.5,
            'max_tokens': 1500,
        },
        TaskType.FORMATTING: {
            'primary': 'groq',             # Fast formatting
            'fallback': 'qwen3',
            'temperature': 0.1,
            'max_tokens': 1000,
        },
        TaskType.DOCUMENTATION: {
            'primary': 'groq',             # Fast doc generation
            'fallback': 'qwen3',
            'temperature': 0.5,
            'max_tokens': 1500,
        },
        TaskType.TESTING: {
            'primary': 'groq',             # Fast test generation
            'fallback': 'qwen3',
            'temperature': 0.4,
            'max_tokens': 2500,
        },
        TaskType.CHAT: {
            'primary': 'groq',             # Fast conversational
            'fallback': 'qwen3',
            'temperature': 0.6,
            'max_tokens': 1500,
        },
        TaskType.GENERAL_HELP: {
            'primary': 'groq',             # Fast general help
            'fallback': 'qwen3',
            'temperature': 0.5,
            'max_tokens': 1500,
        },
    }
    
    @classmethod
    def classify_task(cls, user_input: str, code_context: str = None, error_context: str = None) -> Tuple[TaskType, float]:
        """
        Classify user request into task type
        Returns: (task_type, confidence_score)
        """
        input_lower = user_input.lower()
        
        # Combine all context
        full_context = f"{user_input} {code_context or ''} {error_context or ''}".lower()
        
        # Score each task type
        scores = {}
        
        for task_type, patterns in cls.TASK_PATTERNS.items():
            score = 0.0
            
            # Check each pattern
            for pattern in patterns:
                if re.search(pattern, full_context):
                    score += 1.0
            
            scores[task_type] = score / len(patterns) if patterns else 0
        
        # Find best match
        if not scores or all(s == 0 for s in scores.values()):
            # Default to general help
            return TaskType.GENERAL_HELP, 0.5
        
        best_task = max(scores, key=scores.get)
        confidence = scores[best_task]
        
        return best_task, confidence
    
    @classmethod
    def get_model_recommendation(cls, task_type: TaskType, context_length: int = 0) -> Dict:
        """
        Get model recommendation for task type
        Considers context length and task complexity
        """
        recommendation = cls.PROVIDER_RECOMMENDATIONS.get(
            task_type,
            cls.PROVIDER_RECOMMENDATIONS[TaskType.GENERAL_HELP]
        )
        
        # Adjust tokens based on context
        max_tokens = recommendation['max_tokens']
        if context_length > 3000:  # Large context
            max_tokens = min(max_tokens + 1000, 4000)  # Increase slightly
        
        return {
            'primary_provider': recommendation['primary'],
            'fallback_provider': recommendation['fallback'],
            'temperature': recommendation['temperature'],
            'max_tokens': max_tokens,
            'task_type': task_type.value,
        }
    
    @classmethod
    def route_request(cls, user_input: str, code_context: str = None, error_context: str = None) -> Dict:
        """
        Full routing logic - classify and get recommendation
        """
        # Classify task
        task_type, confidence = cls.classify_task(user_input, code_context, error_context)
        
        # Get recommendation
        context_length = len(code_context or '') + len(error_context or '')
        recommendation = cls.get_model_recommendation(task_type, context_length)
        
        # Add confidence and reasoning
        recommendation['task_confidence'] = confidence
        recommendation['reasoning'] = cls._get_routing_reason(task_type, confidence)
        
        return recommendation
    
    @classmethod
    def _get_routing_reason(cls, task_type: TaskType, confidence: float) -> str:
        """Explain routing decision"""
        reason_map = {
            TaskType.BUG_DIAGNOSIS: "Using DeepSeek R1 for complex reasoning and debugging",
            TaskType.CODE_REVIEW: "Using DeepSeek R1 for thorough code analysis",
            TaskType.OPTIMIZATION: "Using DeepSeek R1 for optimization reasoning",
            TaskType.ARCHITECTURE: "Using DeepSeek R1 for architectural analysis",
            TaskType.CODE_GENERATION: "Using Qwen3 for fast code generation",
            TaskType.AUTO_FIX: "Using Qwen3 for quick code fixes",
            TaskType.COMPLETION: "Using Qwen3 for fast completion",
            TaskType.REFACTORING: "Using Qwen3 for code refactoring",
            TaskType.EXPLANATION: "Using Qwen3 for explanation",
            TaskType.FORMATTING: "Using Qwen3 for code formatting",
            TaskType.DOCUMENTATION: "Using Qwen3 for documentation",
            TaskType.TESTING: "Using Qwen3 for test generation",
            TaskType.CHAT: "Using Qwen3 for conversation",
            TaskType.GENERAL_HELP: "Using Qwen3 for general assistance",
        }
        
        reason = reason_map.get(task_type, "Routing to appropriate model")
        confidence_msg = f" (Confidence: {confidence:.1%})"
        
        return reason + confidence_msg


class ContextAnalyzer:
    """
    Analyzes code context and error context to improve routing
    """
    
    @staticmethod
    def extract_error_type(error_context: str) -> Optional[str]:
        """Extract error type from traceback"""
        if not error_context:
            return None
        
        patterns = [
            r'(SyntaxError|IndentationError)',
            r'(AttributeError|NameError|TypeError)',
            r'(ValueError|KeyError|IndexError)',
            r'(RuntimeError|RecursionError)',
            r'(IOError|OSError)',
            r'(Exception|Error)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_context)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def get_complexity_score(code_context: str) -> float:
        """
        Estimate code complexity (0-1)
        Higher score = more complex = favor DeepSeek R1
        """
        if not code_context:
            return 0.0
        
        score = 0.0
        
        # Complexity indicators
        indicators = {
            r'(async|await|threading|multiprocessing)': 0.3,
            r'(try|except|finally|raise)': 0.2,
            r'(class |def )': 0.1,
            r'(for |while )': 0.1,
            r'(if |elif |else)': 0.05,
            r'(lambda)': 0.1,
            r'(recursion|recursive)': 0.2,
        }
        
        for pattern, weight in indicators.items():
            if re.search(pattern, code_context):
                score += weight
        
        return min(score, 1.0)
