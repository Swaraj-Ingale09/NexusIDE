"""
RAG (Retrieval-Augmented Generation) System for NexusIDE
Provides project context to AI models for better answers
Retrieves relevant project files, similar code, dependencies, etc.
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


class ProjectContextRetriever:
    """
    Retrieves project context for code assistance
    Searches for: related files, dependencies, similar code, documentation
    """
    
    # Max context length (tokens) to avoid overwhelming the model
    MAX_CONTEXT_TOKENS = 4000  # ~15-20KB of text
    
    # File extensions to consider
    RELEVANT_EXTENSIONS = {
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs',
        '.txt', '.md', '.json', '.yaml', '.yml', '.toml', '.xml'
    }
    
    # Files to always include if they exist
    KEY_FILES = [
        'README.md',
        'requirements.txt',
        'package.json',
        'setup.py',
        '.env.example',
        'docker-compose.yml',
        'Dockerfile',
    ]
    
    def __init__(self, project_root: str = None):
        """Initialize with project root directory"""
        self.project_root = project_root or str(settings.BASE_DIR)
        self.file_cache = {}
    
    def get_context(self, current_file: str = None, error_message: str = None, 
                   search_terms: List[str] = None, limit: int = 5) -> Dict:
        """
        Build comprehensive project context
        
        Args:
            current_file: Current file being worked on
            error_message: Error message to search for related files
            search_terms: Terms to search for in project
            limit: Max number of files to include
        
        Returns:
            {
                'project_overview': str,
                'relevant_files': List[str],
                'file_contents': Dict[str, str],
                'dependencies': List[str],
                'error_context': str,
                'similar_code_snippets': List[str],
                'total_context_length': int,
            }
        """
        
        context = {
            'project_overview': self._get_project_overview(),
            'relevant_files': [],
            'file_contents': {},
            'dependencies': self._extract_dependencies(),
            'error_context': self._analyze_error(error_message) if error_message else None,
            'similar_code_snippets': [],
            'total_context_length': 0,
        }
        
        # Find relevant files
        relevant_files = self._find_relevant_files(
            current_file=current_file,
            error_message=error_message,
            search_terms=search_terms,
            limit=limit
        )
        
        # Add file contents until we hit token limit
        token_count = len(context['project_overview'])
        
        for file_path in relevant_files:
            if token_count >= self.MAX_CONTEXT_TOKENS:
                break
            
            try:
                content = self._read_file(file_path, max_lines=100)
                if content:
                    tokens = len(content) // 4  # Rough estimation
                    if token_count + tokens < self.MAX_CONTEXT_TOKENS:
                        context['file_contents'][file_path] = content
                        context['relevant_files'].append(file_path)
                        token_count += tokens
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
        
        context['total_context_length'] = token_count
        
        return context
    
    def _get_project_overview(self) -> str:
        """Get overview of project structure and purpose"""
        overview_parts = []
        
        # Check for README
        readme_path = os.path.join(self.project_root, 'README.md')
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Get first 500 chars
                    overview_parts.append("PROJECT README:\n" + f.read()[:500])
            except:
                pass
        
        # List directory structure (top 2 levels)
        try:
            structure = self._get_directory_tree(self.project_root, max_depth=2)
            overview_parts.append("\nPROJECT STRUCTURE:\n" + structure)
        except:
            pass
        
        return "\n\n".join(overview_parts) or "Project structure information not available"
    
    def _get_directory_tree(self, path: str, prefix: str = "", max_depth: int = 2, current_depth: int = 0) -> str:
        """Generate directory tree string"""
        if current_depth >= max_depth:
            return ""
        
        items = []
        try:
            entries = sorted(os.listdir(path))
            # Filter out common ignored directories
            ignored = {'.git', '__pycache__', '.env', 'node_modules', '.venv', 'venv', 'dist', 'build'}
            entries = [e for e in entries if e not in ignored]
            
            for i, entry in enumerate(entries[:20]):  # Limit to 20 items
                entry_path = os.path.join(path, entry)
                is_dir = os.path.isdir(entry_path)
                
                connector = "├── " if i < len(entries) - 1 else "└── "
                suffix = "/" if is_dir else ""
                items.append(f"{prefix}{connector}{entry}{suffix}")
                
                if is_dir and current_depth < max_depth - 1:
                    new_prefix = prefix + ("│   " if i < len(entries) - 1 else "    ")
                    subtree = self._get_directory_tree(entry_path, new_prefix, max_depth, current_depth + 1)
                    if subtree:
                        items.append(subtree)
        except:
            pass
        
        return "\n".join(items)
    
    def _find_relevant_files(self, current_file: str = None, error_message: str = None,
                            search_terms: List[str] = None, limit: int = 5) -> List[str]:
        """Find most relevant files to include in context"""
        
        from django.core.cache import cache
        
        relevant_files = []
        scores = {}
        
        # Start with key files
        for key_file in self.KEY_FILES:
            path = os.path.join(self.project_root, key_file)
            if os.path.exists(path):
                relevant_files.append(path)
        
        # If current file provided, use it and find related files
        if current_file:
            if os.path.exists(current_file):
                relevant_files.insert(0, current_file)
            
            # Find related files in same directory
            dir_path = os.path.dirname(current_file)
            try:
                for filename in os.listdir(dir_path):
                    filepath = os.path.join(dir_path, filename)
                    if filepath not in relevant_files and self._is_relevant_file(filepath):
                        scores[filepath] = self._score_file_relevance(
                            filepath, current_file, error_message, search_terms
                        )
            except:
                pass
        
        # Search for files matching error message or search terms (cached)
        if error_message or search_terms:
            cache_key = f"rag:filetree:{self.project_root}"
            all_files = cache.get(cache_key)
            if all_files is None:
                all_files = []
                ignore_dirs = {'.git', '__pycache__', '.env', 'node_modules', '.venv', 'venv', 'logs', 'backups'}
                for root, dirs, files in os.walk(self.project_root):
                    dirs[:] = [d for d in dirs if d not in ignore_dirs]
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        if self._is_relevant_file(filepath):
                            all_files.append(filepath)
                cache.set(cache_key, all_files, 300)  # Cache for 5 minutes
            
            for filepath in all_files[:100]:  # Limit search scope
                if filepath not in relevant_files:
                    score = self._score_file_relevance(
                        filepath, current_file, error_message, search_terms
                    )
                    if score > 0:
                        scores[filepath] = score
        
        # Sort by score and add top N
        sorted_files = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for filepath, _ in sorted_files[:limit]:
            if filepath not in relevant_files:
                relevant_files.append(filepath)
        
        return relevant_files[:limit + len(self.KEY_FILES)]
    
    def _is_relevant_file(self, filepath: str) -> bool:
        """Check if file should be considered for context"""
        # Check extension
        _, ext = os.path.splitext(filepath)
        if ext not in self.RELEVANT_EXTENSIONS:
            return False
        
        # Check file size (skip very large files)
        try:
            size = os.path.getsize(filepath)
            if size > 100000:  # 100KB
                return False
        except:
            return False
        
        return True
    
    def _score_file_relevance(self, filepath: str, current_file: str = None,
                             error_message: str = None, search_terms: List[str] = None) -> float:
        """Score how relevant a file is to current context"""
        
        score = 0.0
        
        # Same directory bonus
        if current_file:
            current_dir = os.path.dirname(current_file)
            file_dir = os.path.dirname(filepath)
            if file_dir == current_dir:
                score += 2.0
        
        # Similar filename
        if current_file:
            current_name = os.path.basename(current_file)
            file_name = os.path.basename(filepath)
            if current_name.split('.')[0] in file_name:
                score += 1.5
        
        # Matches search terms
        if search_terms:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for term in search_terms:
                        if term.lower() in content.lower():
                            score += 1.0
            except:
                pass
        
        # Related to error
        if error_message:
            if 'import' in error_message.lower() or 'module' in error_message.lower():
                if filepath.endswith('__init__.py') or filepath.endswith('requirements.txt'):
                    score += 1.5
        
        return score
    
    def _read_file(self, filepath: str, max_lines: int = 100) -> Optional[str]:
        """Read file contents with line limit"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[:max_lines]
                content = ''.join(lines)
                
                # Add file info header
                return f"# File: {filepath}\n```\n{content}\n```"
        except:
            return None
    
    def _extract_dependencies(self) -> List[str]:
        """Extract project dependencies from requirements.txt, package.json, etc."""
        
        dependencies = []
        
        # Check requirements.txt
        req_file = os.path.join(self.project_root, 'requirements.txt')
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Extract package name only
                            pkg = re.split(r'[<>=!]', line)[0].strip()
                            if pkg:
                                dependencies.append(pkg)
            except:
                pass
        
        # Check package.json
        pkg_file = os.path.join(self.project_root, 'package.json')
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    deps = data.get('dependencies', {})
                    dependencies.extend(deps.keys())
            except:
                pass
        
        return dependencies[:20]  # Limit to 20
    
    def _analyze_error(self, error_message: str) -> str:
        """Analyze error message to improve context retrieval"""
        
        analysis = f"ERROR CONTEXT:\n{error_message}\n"
        
        # Extract error type
        error_types = [
            'ImportError', 'ModuleNotFoundError', 'SyntaxError', 'IndentationError',
            'AttributeError', 'NameError', 'TypeError', 'ValueError', 'KeyError',
            'IndexError', 'RuntimeError', 'RecursionError', 'IOError', 'OSError'
        ]
        
        for error_type in error_types:
            if error_type in error_message:
                analysis += f"\nERROR TYPE: {error_type}"
                break
        
        # Extract line/file info
        file_match = re.search(r'File "([^"]+)", line (\d+)', error_message)
        if file_match:
            analysis += f"\nERROR LOCATION: {file_match.group(1)}:{file_match.group(2)}"
        
        return analysis


class CodeSnippetFinder:
    """
    Find similar code snippets in project for reference
    """
    
    @staticmethod
    def find_similar_patterns(code_snippet: str, project_root: str, limit: int = 3) -> List[str]:
        """Find similar code patterns in project"""
        
        similar = []
        
        # Extract patterns from code
        patterns = CodeSnippetFinder._extract_patterns(code_snippet)
        
        if not patterns:
            return similar
        
        # Search project for similar patterns
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.env', 'node_modules', '.venv', 'venv'}]
            
            for filename in files:
                if not filename.endswith(('.py', '.js', '.ts', '.java')):
                    continue
                
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # Check if any patterns match
                        for pattern in patterns:
                            if re.search(pattern, content):
                                similar.append(f"File: {filepath}")
                                break
                except:
                    pass
                
                if len(similar) >= limit:
                    return similar
        
        return similar
    
    @staticmethod
    def _extract_patterns(code_snippet: str) -> List[str]:
        """Extract searchable patterns from code"""
        
        patterns = []
        
        # Extract function/class definitions
        func_pattern = r'def\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, code_snippet):
            patterns.append(f"def {match.group(1)}")
        
        # Extract imports
        import_pattern = r'import\s+(\w+)'
        for match in re.finditer(import_pattern, code_snippet):
            patterns.append(f"import {match.group(1)}")
        
        # Extract class names
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, code_snippet):
            patterns.append(f"class {match.group(1)}")
        
        return patterns[:5]  # Limit to 5 patterns
