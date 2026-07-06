"""
NexusIDE Code Quality Analyzer
Provides real-time linting, complexity analysis, and code metrics
"""
import ast
import re
from typing import Dict, List, Any


class CodeAnalyzer:
    def __init__(self, code: str):
        self.code = code
        self.lines = code.split('\n')
        self.issues = []
        self.metrics = {}

    def analyze(self) -> Dict[str, Any]:
        """Run all analyses and return comprehensive report"""
        self._check_style_issues()
        self._check_complexity()
        self._calculate_metrics()
        self._check_best_practices()
        return {
            'issues': self.issues,
            'metrics': self.metrics,
            'quality_score': self._calculate_quality_score()
        }

    def _check_style_issues(self):
        """Check for common style violations"""
        # Trailing whitespace
        for i, line in enumerate(self.lines, 1):
            if line != line.rstrip():
                self.issues.append({
                    'line': i,
                    'type': 'style',
                    'severity': 'low',
                    'message': 'Trailing whitespace detected',
                    'rule': 'W291'
                })

        # Line too long
        for i, line in enumerate(self.lines, 1):
            if len(line) > 120:
                self.issues.append({
                    'line': i,
                    'type': 'style',
                    'severity': 'low',
                    'message': f'Line too long ({len(line)} > 120 chars)',
                    'rule': 'E501'
                })

        # Missing docstrings
        try:
            tree = ast.parse(self.code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        self.issues.append({
                            'line': node.lineno,
                            'type': 'documentation',
                            'severity': 'medium',
                            'message': f'{node.__class__.__name__} missing docstring',
                            'rule': 'D100'
                        })
        except SyntaxError:
            pass

    def _check_complexity(self):
        """Analyze cyclomatic complexity"""
        try:
            tree = ast.parse(self.code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_function_complexity(node)
                    if complexity > 10:
                        self.issues.append({
                            'line': node.lineno,
                            'type': 'complexity',
                            'severity': 'high',
                            'message': f'Function complexity too high: {complexity}',
                            'rule': 'C901'
                        })
        except SyntaxError:
            pass

    def _calculate_function_complexity(self, node) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _calculate_metrics(self):
        """Calculate code metrics"""
        self.metrics = {
            'total_lines': len(self.lines),
            'code_lines': sum(1 for line in self.lines if line.strip() and not line.strip().startswith('#')),
            'comment_lines': sum(1 for line in self.lines if line.strip().startswith('#')),
            'blank_lines': sum(1 for line in self.lines if not line.strip()),
            'functions': 0,
            'classes': 0,
            'imports': len([l for l in self.lines if 'import' in l])
        }

        try:
            tree = ast.parse(self.code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.metrics['functions'] += 1
                elif isinstance(node, ast.ClassDef):
                    self.metrics['classes'] += 1
        except SyntaxError:
            pass

    def _check_best_practices(self):
        """Check for common anti-patterns and best practices"""
        # Bare except
        if 'except:' in self.code:
            for i, line in enumerate(self.lines, 1):
                if 'except:' in line:
                    self.issues.append({
                        'line': i,
                        'type': 'best_practice',
                        'severity': 'high',
                        'message': 'Bare except clause detected; specify exception type',
                        'rule': 'E722'
                    })

        # Unused imports (simple check)
        imports = re.findall(r'from\s+(\w+)\s+import\s+(\w+)|import\s+(\w+)', self.code)
        for match in imports:
            module = match[2] or match[0]
            if module not in self.code.replace('import ', ''):
                self.issues.append({
                    'line': 1,
                    'type': 'best_practice',
                    'severity': 'low',
                    'message': f'Unused import: {module}',
                    'rule': 'F401'
                })

    def _calculate_quality_score(self) -> int:
        """Calculate 0-100 quality score"""
        score = 100
        for issue in self.issues:
            severity_weight = {'low': 2, 'medium': 5, 'high': 15}
            score -= severity_weight.get(issue['severity'], 3)
        return max(0, score)
