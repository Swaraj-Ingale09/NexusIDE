"""
Self-Refactoring Engine
Analyzes and automatically improves NexusIDE codebase
"""

import os
import re
import json
import ast
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CodeQualityAnalyzer:
    """Analyzes code quality and identifies improvement opportunities"""
    
    # Quality rules
    RULES = {
        'line_length': {'max': 88, 'severity': 'low'},  # Black standard
        'function_complexity': {'max': 10, 'severity': 'medium'},  # Cyclomatic
        'function_length': {'max': 50, 'severity': 'medium'},  # Lines per function
        'docstring_missing': {'severity': 'high'},
        'type_hints_missing': {'severity': 'medium'},
        'duplicate_code': {'similarity': 0.8, 'severity': 'medium'},
        'unused_imports': {'severity': 'low'},
        'unused_variables': {'severity': 'low'},
        'too_many_args': {'max': 5, 'severity': 'medium'},
    }
    
    def __init__(self):
        self.issues = []
        self.metrics = {}
    
    def analyze_file(self, filepath: str) -> Dict:
        """Analyze a Python file for quality issues"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return {'error': str(e)}
        
        self.issues = []
        
        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {'error': f'Syntax error: {e}'}
        
        # Run analysis
        self._check_line_length(code)
        self._check_docstrings(tree)
        self._check_type_hints(tree)
        self._check_function_complexity(tree)
        self._check_function_length(code, tree)
        self._check_unused_imports(code, tree)
        self._check_too_many_args(tree)
        
        return {
            'filepath': filepath,
            'issues': self.issues,
            'metrics': self._calculate_metrics(code, tree),
            'quality_score': self._calculate_quality_score(),
        }
    
    def _check_line_length(self, code: str):
        """Check for lines exceeding max length"""
        max_length = self.RULES['line_length']['max']
        
        for line_num, line in enumerate(code.split('\n'), 1):
            if len(line) > max_length:
                self.issues.append({
                    'type': 'line_too_long',
                    'line': line_num,
                    'length': len(line),
                    'max': max_length,
                    'severity': 'low',
                    'message': f'Line {line_num} is {len(line)} chars (max {max_length})',
                    'fix': 'Break into multiple lines'
                })
    
    def _check_docstrings(self, tree: ast.AST):
        """Check for missing docstrings"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if not docstring:
                    self.issues.append({
                        'type': 'missing_docstring',
                        'line': node.lineno,
                        'name': node.name,
                        'severity': 'high',
                        'message': f'{node.__class__.__name__} "{node.name}" has no docstring',
                        'fix': 'Add docstring explaining purpose and parameters'
                    })
    
    def _check_type_hints(self, tree: ast.AST):
        """Check for missing type hints"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check parameters
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != 'self':
                        self.issues.append({
                            'type': 'missing_type_hint',
                            'line': node.lineno,
                            'name': arg.arg,
                            'severity': 'low',
                            'message': f'Parameter "{arg.arg}" in "{node.name}" lacks type hint',
                            'fix': f'Add type hint: {arg.arg}: SomeType'
                        })
                
                # Check return type
                if node.returns is None and node.name not in ['__init__']:
                    self.issues.append({
                        'type': 'missing_return_type',
                        'line': node.lineno,
                        'name': node.name,
                        'severity': 'low',
                        'message': f'Function "{node.name}" lacks return type hint',
                        'fix': 'Add return type: -> ReturnType'
                    })
    
    def _check_function_complexity(self, tree: ast.AST):
        """Check cyclomatic complexity"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                max_complexity = self.RULES['function_complexity']['max']
                
                if complexity > max_complexity:
                    self.issues.append({
                        'type': 'high_complexity',
                        'line': node.lineno,
                        'name': node.name,
                        'complexity': complexity,
                        'max': max_complexity,
                        'severity': 'medium',
                        'message': f'Function "{node.name}" has complexity {complexity} (max {max_complexity})',
                        'fix': 'Break into smaller functions or simplify logic'
                    })
    
    def _check_function_length(self, code: str, tree: ast.AST):
        """Check function length"""
        lines = code.split('\n')
        max_length = self.RULES['function_length']['max']
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_length = node.end_lineno - node.lineno
                
                if func_length > max_length:
                    self.issues.append({
                        'type': 'function_too_long',
                        'line': node.lineno,
                        'name': node.name,
                        'length': func_length,
                        'max': max_length,
                        'severity': 'medium',
                        'message': f'Function "{node.name}" is {func_length} lines (max {max_length})',
                        'fix': 'Extract helper functions'
                    })
    
    def _check_unused_imports(self, code: str, tree: ast.AST):
        """Check for unused imports"""
        imported = set()
        used = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add(alias.asname or alias.name)
            elif isinstance(node, ast.Name):
                used.add(node.id)
        
        unused = imported - used
        for name in unused:
            self.issues.append({
                'type': 'unused_import',
                'name': name,
                'severity': 'low',
                'message': f'Import "{name}" is unused',
                'fix': f'Remove: import {name}'
            })
    
    def _check_too_many_args(self, tree: ast.AST):
        """Check for functions with too many parameters"""
        max_args = self.RULES['too_many_args']['max']
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                arg_count = len(node.args.args)
                if arg_count > max_args:
                    self.issues.append({
                        'type': 'too_many_args',
                        'line': node.lineno,
                        'name': node.name,
                        'count': arg_count,
                        'max': max_args,
                        'severity': 'medium',
                        'message': f'Function "{node.name}" has {arg_count} parameters (max {max_args})',
                        'fix': 'Use dataclass or config object instead'
                    })
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _calculate_metrics(self, code: str, tree: ast.AST) -> Dict:
        """Calculate code metrics"""
        lines = code.split('\n')
        
        return {
            'total_lines': len(lines),
            'blank_lines': len([l for l in lines if not l.strip()]),
            'comment_lines': len([l for l in lines if l.strip().startswith('#')]),
            'functions': len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
            'classes': len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]),
        }
    
    def _calculate_quality_score(self) -> int:
        """Calculate overall quality score (0-100)"""
        if not self.issues:
            return 100
        
        score = 100
        for issue in self.issues:
            severity_weight = {
                'low': 2,
                'medium': 5,
                'high': 10,
            }
            score -= severity_weight.get(issue.get('severity', 'low'), 5)
        
        return max(0, score)


class CodeRefactorer:
    """Automatically refactors code to improve quality"""
    
    def __init__(self):
        self.refactoring_log = []
    
    def refactor_file(self, filepath: str, issues: List[Dict]) -> Dict:
        """Refactor a file based on identified issues"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original_code = f.read()
        except Exception as e:
            return {'error': str(e)}
        
        refactored_code = original_code
        changes = []
        
        # Group issues by line for efficient processing
        line_issues = {}
        for issue in issues:
            line_num = issue.get('line')
            if line_num:
                if line_num not in line_issues:
                    line_issues[line_num] = []
                line_issues[line_num].append(issue)
        
        # Apply fixes for each issue type
        refactored_code, new_changes = self._fix_missing_docstrings(refactored_code, issues)
        changes.extend(new_changes)
        
        refactored_code, new_changes = self._fix_missing_type_hints(refactored_code, issues)
        changes.extend(new_changes)
        
        refactored_code, new_changes = self._fix_line_length(refactored_code, issues)
        changes.extend(new_changes)
        
        refactored_code, new_changes = self._fix_unused_imports(refactored_code, issues)
        changes.extend(new_changes)
        
        refactored_code, new_changes = self._fix_too_many_args(refactored_code, issues)
        changes.extend(new_changes)
        
        refactored_code, new_changes = self._fix_blank_lines(refactored_code)
        changes.extend(new_changes)
        
        return {
            'filepath': filepath,
            'original_lines': len(original_code.split('\n')),
            'refactored_lines': len(refactored_code.split('\n')),
            'changes': changes,
            'changes_count': len(changes),
            'refactored_code': refactored_code,
        }
    
    def _fix_missing_docstrings(self, code: str, issues: List[Dict]) -> Tuple[str, List[Dict]]:
        """Add missing docstrings to functions and classes"""
        changes = []
        lines = code.split('\n')
        
        docstring_issues = [i for i in issues if i.get('type') == 'missing_docstring']
        
        for issue in sorted(docstring_issues, key=lambda x: x.get('line', 0), reverse=True):
            line_num = issue.get('line', 1) - 1
            name = issue.get('name', 'unknown')
            
            if line_num >= len(lines):
                continue
            
            line = lines[line_num]
            indent = len(line) - len(line.lstrip())
            indent_str = ' ' * (indent + 4)
            
            # Find the colon that ends the def/class line
            colon_line = line_num
            if not line.rstrip().endswith(':'):
                # Multi-line definition - find the colon
                for i in range(line_num, min(line_num + 10, len(lines))):
                    if lines[i].rstrip().endswith(':'):
                        colon_line = i
                        break
            
            # Create docstring
            description = f"{name.replace('_', ' ').title()} implementation."
            docstring_lines = [
                f'{indent_str}"""',
                f'{indent_str}{description}',
                f'{indent_str}"""'
            ]
            
            # Insert docstring after the colon line
            for doc_line in reversed(docstring_lines):
                lines.insert(colon_line + 1, doc_line)
            
            changes.append({
                'type': 'docstring_added',
                'line': colon_line + 1,
                'name': name
            })
        
        return '\n'.join(lines), changes
    
    def _fix_missing_type_hints(self, code: str, issues: List[Dict]) -> Tuple[str, List[Dict]]:
        """Add missing type hints - SKIP for now to avoid syntax errors"""
        changes = []
        # Type hints are complex and can cause syntax errors, so we skip them
        # Users should add type hints manually or use type checkers
        return code, changes
    
    def _fix_line_length(self, code: str, issues: List[Dict]) -> Tuple[str, List[Dict]]:
        """Fix lines that are too long by breaking them intelligently"""
        changes = []
        lines = code.split('\n')
        
        length_issues = [i for i in issues if i.get('type') == 'line_too_long']
        
        for issue in sorted(length_issues, key=lambda x: x.get('line', 0), reverse=True):
            line_num = issue.get('line', 1) - 1
            
            if line_num >= len(lines):
                continue
            
            line = lines[line_num]
            max_length = issue.get('max', 88)
            
            if len(line) > max_length:
                # Get indent
                indent = len(line) - len(line.lstrip())
                indent_str = line[:indent]
                content = line[indent:]
                
                # Strategy 1: Break at commas (for function calls, dict/list literals)
                if ',' in content:
                    fixed_line = self._break_at_commas_smart(content, max_length, indent_str)
                    if '\n' in fixed_line:
                        # Successfully broke the line
                        new_lines = fixed_line.split('\n')
                        lines[line_num] = new_lines[0]
                        for new_line in new_lines[1:]:
                            lines.insert(line_num + 1, new_line)
                        changes.append({
                            'type': 'line_length_fixed',
                            'line': line_num + 1,
                            'from': len(line),
                            'to': len(new_lines[0])
                        })
                        continue
                
                # Strategy 2: Break after operators (+, -, *, etc)
                if any(op in content for op in [' + ', ' - ', ' and ', ' or ']):
                    fixed_line = self._break_at_operators(content, max_length, indent_str)
                    if '\n' in fixed_line:
                        new_lines = fixed_line.split('\n')
                        lines[line_num] = new_lines[0]
                        for new_line in new_lines[1:]:
                            lines.insert(line_num + 1, new_line)
                        changes.append({
                            'type': 'line_length_fixed',
                            'line': line_num + 1,
                            'from': len(line),
                            'to': len(new_lines[0])
                        })
        
        return '\n'.join(lines), changes
    
    def _break_at_commas_smart(self, content: str, max_length: int, indent_str: str) -> str:
        """Break line at commas intelligently"""
        continuation_indent = indent_str + '    '
        
        # Find the opening parenthesis or bracket
        paren_pos = content.find('(')
        bracket_pos = content.find('{')
        bracket_list_pos = content.find('[')
        
        start_pos = -1
        for pos in [paren_pos, bracket_pos, bracket_list_pos]:
            if pos >= 0 and (start_pos < 0 or pos < start_pos):
                start_pos = pos
        
        if start_pos < 0:
            return content  # No brackets/parens, can't break smartly
        
        # Break line at commas after the opening bracket
        before_bracket = content[:start_pos + 1]
        after_bracket = content[start_pos + 1:]
        
        if ',' not in after_bracket:
            return content  # No commas to break on
        
        # Split by comma and rejoin with proper indentation
        parts = after_bracket.split(',')
        
        if len(parts) < 2:
            return content
        
        # Build the fixed line
        result = [before_bracket]
        for i, part in enumerate(parts[:-1]):
            result.append('\n' + continuation_indent + part.strip() + ',')
        result.append('\n' + continuation_indent + parts[-1].strip())
        
        return ''.join(result)
    
    def _break_at_operators(self, content: str, max_length: int, indent_str: str) -> str:
        """Break line at operators"""
        continuation_indent = indent_str + '    '
        
        operators = [' and ', ' or ', ' + ', ' - ', ' * ', ' / ']
        
        for op in operators:
            if op in content:
                parts = content.split(op)
                if len(parts) >= 2:
                    result = [parts[0].rstrip()]
                    for i, part in enumerate(parts[1:]):
                        result.append('\n' + continuation_indent + op.strip() + ' ' + part.lstrip())
                    return ''.join(result)
        
        return content
    
    def _fix_unused_imports(self, code: str, issues: List[Dict]) -> Tuple[str, List[Dict]]:
        """Remove unused imports"""
        changes = []
        lines = code.split('\n')
        
        unused_issues = [i for i in issues if i.get('type') == 'unused_import']
        
        for issue in sorted(unused_issues, key=lambda x: x.get('line', 0), reverse=True):
            import_name = issue.get('name')
            
            # Find and remove the import line
            for i, line in enumerate(lines):
                if f'import {import_name}' in line or f'from' in line and import_name in line:
                    # Check if it's the whole line or part of a multi-import
                    if f', {import_name}' in line:
                        # Part of multi-import
                        lines[i] = line.replace(f', {import_name}', '')
                        changes.append({
                            'type': 'import_removed',
                            'import': import_name,
                            'line': i + 1
                        })
                        break
                    elif f'{import_name}, ' in line:
                        lines[i] = line.replace(f'{import_name}, ', '')
                        changes.append({
                            'type': 'import_removed',
                            'import': import_name,
                            'line': i + 1
                        })
                        break
                    else:
                        # Entire line is this import
                        lines[i] = ''
                        changes.append({
                            'type': 'import_removed',
                            'import': import_name,
                            'line': i + 1
                        })
                        break
        
        return '\n'.join(lines), changes
    
    def _fix_too_many_args(self, code: str, issues: List[Dict]) -> Tuple[str, List[Dict]]:
        """Suggest fixes for functions with too many arguments"""
        changes = []
        
        too_many_args_issues = [i for i in issues if i.get('type') == 'too_many_args']
        
        for issue in too_many_args_issues:
            changes.append({
                'type': 'too_many_args_noted',
                'function': issue.get('name'),
                'line': issue.get('line'),
                'suggestion': 'Consider using a dataclass or config object to group parameters'
            })
        
        return code, changes
    
    def _fix_blank_lines(self, code: str) -> Tuple[str, List[Dict]]:
        """Fix excessive blank lines (max 2 consecutive)"""
        changes = []
        lines = code.split('\n')
        fixed_lines = []
        blank_count = 0
        
        for line in lines:
            if line.strip() == '':
                blank_count += 1
                if blank_count <= 2:  # Allow max 2 consecutive blank lines
                    fixed_lines.append(line)
            else:
                blank_count = 0
                fixed_lines.append(line)
        
        fixed_code = '\n'.join(fixed_lines)
        
        if fixed_code != code:
            changes.append({
                'type': 'excessive_blank_lines_fixed',
                'lines_removed': len(lines) - len(fixed_lines)
            })
        
        return fixed_code, changes
    
    def _break_long_line(self, line: str, max_length: int) -> str:
        """Break a long line at logical points"""
        if len(line) <= max_length:
            return line
        
        # Get indentation
        indent = len(line) - len(line.lstrip())
        indent_str = line[:indent]
        continuation_indent = indent_str + '    '
        
        # Try to break at opening parenthesis
        if '(' in line:
            parts = line.split('(', 1)
            if len(parts) == 2:
                before = parts[0] + '('
                after = parts[1]
                
                if ',' in after:
                    # Break at commas
                    args = after.split(',')
                    result = [before]
                    for i, arg in enumerate(args[:-1]):
                        result.append(continuation_indent + arg.strip() + ',')
                    result.append(continuation_indent + args[-1].strip())
                    return '\n'.join(result)
        
        return line
    
    def _break_at_commas(self, line: str, max_length: int) -> str:
        """Break a line at commas"""
        if len(line) <= max_length or ',' not in line:
            return line
        
        indent = len(line) - len(line.lstrip())
        indent_str = line[:indent]
        continuation_indent = indent_str + '    '
        
        parts = line.split(',')
        result = []
        
        for i, part in enumerate(parts[:-1]):
            result.append(part.rstrip() + ',')
        result.append(parts[-1])
        
        return ('\n' + continuation_indent).join(result)


class AutoRefactoringEngine:
    """Main engine for automatic code refactoring"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.analyzer = CodeQualityAnalyzer()
        self.refactorer = CodeRefactorer()
        self.refactoring_history = []
    
    def analyze_directory(self, directory: str = None, exclude_dirs: List[str] = None) -> Dict:
        """Analyze all Python files in directory"""
        if directory is None:
            directory = self.project_root
        
        exclude_dirs = exclude_dirs or ['venv', '__pycache__', '.git', 'node_modules']
        
        results = {
            'directory': directory,
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': 0,
            'total_issues': 0,
            'quality_score': 0,
            'files': [],
        }
        
        py_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    py_files.append(os.path.join(root, file))
        
        total_quality = 0
        
        for filepath in py_files:
            analysis = self.analyzer.analyze_file(filepath)
            
            if 'error' not in analysis:
                results['files_analyzed'] += 1
                results['total_issues'] += len(analysis['issues'])
                total_quality += analysis['quality_score']
                
                results['files'].append({
                    'filepath': filepath,
                    'issues_count': len(analysis['issues']),
                    'quality_score': analysis['quality_score'],
                    'metrics': analysis['metrics'],
                    'issues': analysis['issues'][:5],  # Top 5 issues
                })
        
        if results['files_analyzed'] > 0:
            results['quality_score'] = round(total_quality / results['files_analyzed'], 2)
        
        return results
    
    def auto_refactor_file(self, filepath: str, apply_changes: bool = False) -> Dict:
        """Automatically refactor a single file"""
        # Analyze
        analysis = self.analyzer.analyze_file(filepath)
        
        if 'error' in analysis:
            return analysis
        
        # Refactor
        refactoring = self.refactorer.refactor_file(filepath, analysis['issues'])
        
        # Apply changes if requested
        if apply_changes and 'refactored_code' in refactoring:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(refactoring['refactored_code'])
                refactoring['applied'] = True
            except Exception as e:
                refactoring['error'] = str(e)
                refactoring['applied'] = False
        else:
            refactoring['applied'] = False
        
        # Log
        self.refactoring_history.append({
            'filepath': filepath,
            'timestamp': datetime.now().isoformat(),
            'issues': len(analysis['issues']),
            'changes': refactoring.get('changes_count', 0),
            'applied': refactoring.get('applied', False),
        })
        
        return refactoring
    
    def auto_refactor_directory(self, directory: str = None, apply_changes: bool = False) -> Dict:
        """Auto-refactor all Python files in directory"""
        if directory is None:
            directory = self.project_root
        
        analysis = self.analyze_directory(directory)
        
        refactored_files = []
        total_changes = 0
        
        for file_info in analysis['files']:
            filepath = file_info['filepath']
            result = self.auto_refactor_file(filepath, apply_changes)
            
            if 'changes' in result:
                refactored_files.append({
                    'filepath': filepath,
                    'changes': result.get('changes_count', 0),
                    'applied': result.get('applied', False),
                })
                total_changes += result.get('changes_count', 0)
        
        return {
            'directory': directory,
            'files_analyzed': analysis['files_analyzed'],
            'files_refactored': len(refactored_files),
            'total_changes': total_changes,
            'average_quality_before': analysis['quality_score'],
            'files': refactored_files,
            'applied': apply_changes,
        }
    
    def generate_quality_report(self) -> Dict:
        """Generate comprehensive quality report"""
        analysis = self.analyze_directory()
        
        # Group by severity
        issues_by_severity = {'high': 0, 'medium': 0, 'low': 0}
        issues_by_type = {}
        
        for file_info in analysis['files']:
            for issue in file_info.get('issues', []):
                severity = issue.get('severity', 'low')
                issues_by_severity[severity] += 1
                
                issue_type = issue.get('type', 'unknown')
                issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_files': analysis['files_analyzed'],
                'total_issues': analysis['total_issues'],
                'overall_quality_score': analysis['quality_score'],
            },
            'issues_by_severity': issues_by_severity,
            'issues_by_type': issues_by_type,
            'files': sorted(
                analysis['files'],
                key=lambda x: x['quality_score']
            )[:10],  # Bottom 10 files
            'refactoring_history': self.refactoring_history[-20:],  # Last 20 refactorings
        }


# Singleton instance
_refactoring_engine = None


def get_refactoring_engine(project_root: str = None) -> AutoRefactoringEngine:
    """Get or create refactoring engine instance"""
    global _refactoring_engine
    if _refactoring_engine is None:
        _refactoring_engine = AutoRefactoringEngine(project_root)
    return _refactoring_engine
