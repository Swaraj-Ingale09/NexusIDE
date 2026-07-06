"""
Language Detection - PYTHON, C, C++ ONLY
Auto-detects: Python, C, C++ languages
"""

import re
import logging

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detects PYTHON, C, C++ ONLY"""
    
    LANGUAGE_PATTERNS = {
        'python': [
            r'^\s*import\s+\w+',
            r'^\s*from\s+\w+\s+import',
            r'^\s*def\s+\w+\s*\(',
            r'^\s*class\s+\w+',
            r'print\s*\(',
            r'for\s+\w+\s+in\s+',
        ],
        'c': [
            r'#include\s*<\w+\.h>',
            r'int\s+main\s*\(',
            r'printf\s*\(',
            r'scanf\s*\(',
            r'malloc\s*\(',
            r'free\s*\(',
        ],
        'cpp': [
            r'#include\s*<iostream>',
            r'using\s+namespace\s+std',
            r'std::\w+',
            r'cout\s*<<',
            r'cin\s*>>',
            r'new\s+\w+',
        ],
    }
    
    EXTENSION_MAP = {
        '.py': 'python',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.hpp': 'cpp',
    }
    
    @staticmethod
    def detect(code: str, filename: str = None) -> str:
        """Detect language: python, c, or cpp"""
        if not code or not code.strip():
            return 'python'
        
        if filename:
            for ext, lang in LanguageDetector.EXTENSION_MAP.items():
                if filename.lower().endswith(ext):
                    logger.info(f"Detected {lang} from filename: {filename}")
                    return lang
        
        scores = {}
        for language, patterns in LanguageDetector.LANGUAGE_PATTERNS.items():
            score = sum(len(re.findall(p, code, re.IGNORECASE | re.MULTILINE)) for p in patterns)
            scores[language] = score
        
        if scores and max(scores.values()) > 0:
            detected = max(scores, key=scores.get)
            logger.info(f"Detected {detected}")
            return detected
        
        return 'python'
    
    @staticmethod
    def get_language_info(language: str) -> dict:
        """Get info for language"""
        info = {
            'python': {
                'name': 'Python',
                'extensions': ['.py'],
                'icon': '🐍',
                'description': 'Python - General purpose programming',
            },
            'c': {
                'name': 'C',
                'extensions': ['.c', '.h'],
                'icon': '🔤',
                'description': 'C - Systems programming',
            },
            'cpp': {
                'name': 'C++',
                'extensions': ['.cpp', '.cc', '.cxx', '.hpp'],
                'icon': '⚙️',
                'description': 'C++ - Object-oriented programming',
            },
        }
        return info.get(language.lower(), {'name': language, 'icon': '💻'})
    
    @staticmethod
    def get_supported_languages() -> list:
        """Get supported languages"""
        return ['python', 'c', 'cpp']
