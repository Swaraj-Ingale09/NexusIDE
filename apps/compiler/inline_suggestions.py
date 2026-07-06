"""
In-Line Code Suggestions
Shows real-time suggestions as user types
No complex integration needed - just simple, fast suggestions
"""

import re
from typing import Dict, List


class InlineSuggestions:
    """Generates inline code suggestions on-the-fly"""
    
    def __init__(self):
        self.common_issues = {
            'unused_imports': self._suggest_remove_import,
            'missing_docstring': self._suggest_add_docstring,
            'long_line': self._suggest_break_line,
            'unused_variable': self._suggest_remove_variable,
            'simple_bool': self._suggest_simplify_bool,
            'bad_naming': self._suggest_better_name,
        }
    
    def get_suggestions(self, code: str, line_num: int = None) -> List[Dict]:
        """Get all suggestions for code"""
        suggestions = []
        lines = code.split('\n')
        
        # Check each line for issues
        for i, line in enumerate(lines, 1):
            if line_num and i != line_num:
                continue
            
            # Check for various issues
            if self._is_long_line(line):
                suggestions.append({
                    'type': 'long_line',
                    'line': i,
                    'current': line.strip(),
                    'suggestion': self._suggest_break_line(line),
                    'severity': 'info',
                    'message': 'Line is too long (88+ chars)'
                })
            
            if self._is_unused_import(line):
                suggestions.append({
                    'type': 'unused_import',
                    'line': i,
                    'current': line.strip(),
                    'suggestion': '',
                    'severity': 'warning',
                    'message': 'This import is likely unused'
                })
            
            if self._is_missing_docstring(line):
                suggestions.append({
                    'type': 'missing_docstring',
                    'line': i,
                    'current': line.strip(),
                    'suggestion': self._suggest_add_docstring(line),
                    'severity': 'info',
                    'message': 'Add a docstring to explain this'
                })
            
            if self._is_simple_bool(line):
                suggestions.append({
                    'type': 'simple_bool',
                    'line': i,
                    'current': line.strip(),
                    'suggestion': self._suggest_simplify_bool(line),
                    'severity': 'info',
                    'message': 'Can simplify boolean logic'
                })
            
            if self._is_bad_naming(line):
                suggestions.append({
                    'type': 'bad_naming',
                    'line': i,
                    'current': line.strip(),
                    'suggestion': self._suggest_better_name(line),
                    'severity': 'info',
                    'message': 'Variable name could be clearer'
                })
        
        return suggestions
    
    def _is_long_line(self, line: str) -> bool:
        """Check if line exceeds 88 characters"""
        return len(line) > 88 and not line.strip().startswith('#')
    
    def _is_unused_import(self, line: str) -> bool:
        """Check if line is an unused import"""
        if not line.strip().startswith(('import ', 'from ')):
            return False
        # Common unused imports
        return any(x in line for x in ['unused', 'os', 'sys', 'typing.List', 'json'])
    
    def _is_missing_docstring(self, line: str) -> bool:
        """Check if function/class needs docstring"""
        stripped = line.strip()
        # Check if it's a function or class definition
        if stripped.startswith(('def ', 'class ')):
            # This is simplified - in real code you'd check the next line
            return not any(x in line for x in ['"""', "'''"])
        return False
    
    def _is_simple_bool(self, line: str) -> bool:
        """Check for simple boolean logic that can be simplified"""
        return any(pattern in line for pattern in [
            'return True if',
            'return False if',
            'if x:\n        return True\n    else:\n        return False',
        ])
    
    def _is_bad_naming(self, line: str) -> bool:
        """Check for poorly named variables"""
        bad_names = ['x = ', 'y = ', 'z = ', 'tmp = ', 't = ', 'foo = ', 'bar = ']
        return any(name in line for name in bad_names)
    
    def _suggest_break_line(self, line: str) -> str:
        """Suggest how to break a long line"""
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        continuation = indent_str + '    '
        
        # Try to break at commas
        if '(' in line and ')' in line and ',' in line:
            # Extract arguments
            match = re.search(r'\((.*?)\)', line)
            if match:
                args = match.group(1).split(',')
                if len(args) > 2:
                    before = line[:match.start() + 1]
                    after = line[match.end():]
                    
                    suggestion_parts = [before]
                    for arg in args[:-1]:
                        suggestion_parts.append(f'\n{continuation}{arg.strip()},')
                    suggestion_parts.append(f'\n{continuation}{args[-1].strip()}')
                    suggestion_parts.append(f'\n{indent_str}{after}')
                    
                    return ''.join(suggestion_parts)
        
        # Try to break at dictionary
        if '{' in line and '}' in line and ':' in line:
            return f"{line[:line.find('{') + 1]}\n{continuation}...\n{indent_str}}}"
        
        # Just suggest breaking with comment
        return f"# Line too long, break it up:\n{line}"
    
    def _suggest_add_docstring(self, line: str) -> str:
        """Suggest docstring"""
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        doc_indent = indent_str + '    '
        
        # Extract function/class name
        match = re.search(r'(?:def|class)\s+(\w+)', line)
        if match:
            name = match.group(1).replace('_', ' ').title()
            return f'{line}\n{doc_indent}"""{name} implementation."""'
        
        return f'{line}\n{doc_indent}"""TODO: Add docstring."""'
    
    def _suggest_simplify_bool(self, line: str) -> str:
        """Suggest simplified boolean"""
        # Pattern: if x: return True else: return False
        if 'if' in line and 'return True' in line:
            # Extract condition
            match = re.search(r'if\s+(.+?):', line)
            if match:
                condition = match.group(1).strip()
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                return f'{indent_str}return {condition}'
        
        return line
    
    def _suggest_better_name(self, line: str) -> str:
        """Suggest better variable name"""
        suggestions_map = {
            'x': 'value',
            'y': 'count',
            'z': 'total',
            'tmp': 'temporary',
            't': 'time',
            'foo': 'data',
            'bar': 'result',
        }
        
        result = line
        for bad, good in suggestions_map.items():
            if f'{bad} = ' in result:
                result = result.replace(f'{bad} = ', f'{good} = ')
                break
        
        return result


class QuickFix:
    """Quick fixes that can be applied immediately"""
    
    @staticmethod
    def apply_suggestion(code: str, suggestion: Dict) -> str:
        """Apply a single suggestion to code"""
        lines = code.split('\n')
        line_num = suggestion['line'] - 1
        
        if line_num >= len(lines):
            return code
        
        suggestion_type = suggestion['type']
        
        if suggestion_type == 'unused_import':
            # Remove the line
            lines.pop(line_num)
        
        elif suggestion_type == 'missing_docstring':
            # Add docstring
            new_suggestion = suggestion.get('suggestion', '')
            if new_suggestion:
                lines[line_num] = new_suggestion
        
        elif suggestion_type == 'simple_bool':
            # Simplify
            new_suggestion = suggestion.get('suggestion', '')
            if new_suggestion:
                lines[line_num] = new_suggestion
        
        elif suggestion_type == 'bad_naming':
            # Rename
            new_suggestion = suggestion.get('suggestion', '')
            if new_suggestion:
                lines[line_num] = new_suggestion
        
        elif suggestion_type == 'long_line':
            # Replace with suggestion
            new_suggestion = suggestion.get('suggestion', '')
            if new_suggestion:
                # Handle multi-line suggestions
                if '\n' in new_suggestion:
                    new_lines = new_suggestion.split('\n')
                    lines[line_num:line_num+1] = new_lines
                else:
                    lines[line_num] = new_suggestion
        
        return '\n'.join(lines)
    
    @staticmethod
    def apply_all_suggestions(code: str, suggestions: List[Dict]) -> str:
        """Apply all suggestions (in reverse order to maintain line numbers)"""
        result = code
        
        for suggestion in reversed(sorted(suggestions, key=lambda x: x['line'])):
            result = QuickFix.apply_suggestion(result, suggestion)
        
        return result


def get_inline_suggestions(code: str, line_num: int = None) -> List[Dict]:
    """Get inline suggestions for code"""
    suggester = InlineSuggestions()
    return suggester.get_suggestions(code, line_num)


def apply_inline_suggestion(code: str, suggestion: Dict) -> str:
    """Apply a single inline suggestion"""
    return QuickFix.apply_suggestion(code, suggestion)


def apply_all_inline_suggestions(code: str, suggestions: List[Dict]) -> str:
    """Apply all inline suggestions"""
    return QuickFix.apply_all_suggestions(code, suggestions)
