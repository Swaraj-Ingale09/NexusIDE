"""
NexusIDE Code Formatter
Auto-formats Python code to PEP 8 standards
"""
import re


class PythonFormatter:
    """Simple Python code formatter (PEP 8 compliant)"""

    def format(self, code: str) -> str:
        """Format Python code"""
        lines = code.split('\n')
        formatted_lines = []

        for line in lines:
            formatted = self._format_line(line)
            formatted_lines.append(formatted)

        # Remove excessive blank lines (max 2 consecutive)
        final_lines = []
        blank_count = 0
        for line in formatted_lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    final_lines.append(line)
            else:
                blank_count = 0
                final_lines.append(line)

        return '\n'.join(final_lines)

    def _format_line(self, line: str) -> str:
        """Format a single line"""
        # Skip empty or comment-only lines
        if not line.strip() or line.strip().startswith('#'):
            return line

        # Remove trailing whitespace
        line = line.rstrip()

        # Normalize spacing around operators
        line = self._fix_operator_spacing(line)

        # Normalize spacing in function definitions/calls
        line = self._fix_spacing_in_parens(line)

        # Normalize spacing after keywords
        line = self._fix_keyword_spacing(line)

        return line

    def _fix_operator_spacing(self, line: str) -> str:
        """Fix spacing around operators (=, +, -, etc.)"""
        # Don't modify lines inside strings or comments
        code_part = line.split('#')[0]

        # Fix spacing around assignment
        code_part = re.sub(r'\s*=\s*(?!=)', ' = ', code_part)
        code_part = re.sub(r'\s*==\s*', ' == ', code_part)
        code_part = re.sub(r'\s*!=\s*', ' != ', code_part)

        # Fix spacing around arithmetic (but preserve ** and ///)
        code_part = re.sub(r'(?<!\*)\+(?!\+)', ' + ', code_part)
        code_part = re.sub(r'(?<!-)-(?!-|>)', ' - ', code_part)
        code_part = re.sub(r'(?<!\*)\*(?!\*)', ' * ', code_part)
        code_part = re.sub(r'(?<!/)/(?!/)', ' / ', code_part)

        # Add back comment if present
        if '#' in line:
            code_part += ' ' + line.split('#', 1)[1]

        return code_part

    def _fix_spacing_in_parens(self, line: str) -> str:
        """Fix spacing inside parentheses, brackets, braces"""
        # No space after opening or before closing
        line = re.sub(r'\(\s+', '(', line)
        line = re.sub(r'\s+\)', ')', line)
        line = re.sub(r'\[\s+', '[', line)
        line = re.sub(r'\s+\]', ']', line)
        line = re.sub(r'{\s+', '{', line)
        line = re.sub(r'\s+}', '}', line)

        # Space after comma
        line = re.sub(r',(?!\s)', ', ', line)

        return line

    def _fix_keyword_spacing(self, line: str) -> str:
        """Fix spacing after keywords"""
        keywords = ['if', 'elif', 'else', 'for', 'while', 'def', 'class', 'return', 'import', 'from']
        for kw in keywords:
            # Add space after keyword if missing (but not in middle of identifier)
            line = re.sub(rf'\b{kw}(?![\w_])\s*', f'{kw} ', line)

        return line