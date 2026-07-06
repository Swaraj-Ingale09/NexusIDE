"""
Python AST Parser for NexusIDE.
Provides real-time code analysis, bug detection, complexity metrics,
dead code detection, and auto-refactoring suggestions.
All analysis runs locally — no AI API calls needed.
"""

import ast
import math
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Severity(Enum):
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    HINT = 'hint'


@dataclass
class CodeIssue:
    """A single code issue detected by the parser."""
    line: int
    column: int
    end_line: int
    end_column: int
    severity: Severity
    code: str  # e.g. "W001", "E001"
    message: str
    suggestion: Optional[str] = None
    fixable: bool = False
    category: str = ''  # bug, complexity, style, dead_code, refactor

    def to_dict(self) -> Dict:
        return {
            'line': self.line,
            'column': self.column,
            'endLine': self.end_line,
            'endColumn': self.end_column,
            'severity': self.severity.value,
            'code': self.code,
            'message': self.message,
            'suggestion': self.suggestion,
            'fixable': self.fixable,
            'category': self.category,
        }


@dataclass
class ComplexityMetrics:
    """Code complexity metrics."""
    cyclomatic: int = 1
    cognitive: int = 0
    halstead_volume: float = 0.0
    maintainability_index: float = 100.0
    lines_of_code: int = 0
    logical_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    functions: int = 0
    classes: int = 0
    max_depth: int = 0
    avg_function_length: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'cyclomatic': self.cyclomatic,
            'cognitive': self.cognitive,
            'halsteadVolume': round(self.halstead_volume, 2),
            'maintainabilityIndex': round(self.maintainability_index, 2),
            'linesOfCode': self.lines_of_code,
            'logicalLines': self.logical_lines,
            'commentLines': self.comment_lines,
            'blankLines': self.blank_lines,
            'functions': self.functions,
            'classes': self.classes,
            'maxDepth': self.max_depth,
            'avgFunctionLength': round(self.avg_function_length, 1),
        }


@dataclass
class AnalysisResult:
    """Complete analysis result for a code file."""
    issues: List[CodeIssue] = field(default_factory=list)
    metrics: ComplexityMetrics = field(default_factory=ComplexityMetrics)
    dependencies: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    ast_valid: bool = True
    parse_error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'issues': [i.to_dict() for i in self.issues],
            'metrics': self.metrics.to_dict(),
            'dependencies': self.dependencies,
            'exports': self.exports,
            'astValid': self.ast_valid,
            'parseError': self.parse_error,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Bug Detection Rules
# ══════════════════════════════════════════════════════════════════════════════

class BugDetector(ast.NodeVisitor):
    """Detects potential bugs in Python code."""

    def __init__(self):
        self.issues: List[CodeIssue] = []
        self._function_names: set = set()
        self._variable_names: set = set()
        self._loop_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._function_names.add(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_For(self, node):
        self._loop_depth += 1
        self._check_unbounded_loop(node)
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node):
        self._loop_depth += 1
        self._check_infinite_loop(node)
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_Compare(self, node):
        self._check_chained_comparison(node)
        self.generic_visit(node)

    def visit_BinOp(self, node):
        self._check_division_by_zero(node)
        self._check_modulo_zero(node)
        self.generic_visit(node)

    def visit_Call(self, node):
        self._check_bare_except_in_call(node)
        self._check_mutable_default(node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self._check_bare_except(node)
        self.generic_visit(node)

    def visit_Return(self, node):
        self._check_return_in_loop(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        self._check_unused_assignment(node)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._check_self_assignment(node)
        self.generic_visit(node)

    def visit_Subscript(self, node):
        self._check_index_out_of_range(node)
        self.generic_visit(node)

    def visit_Name(self, node):
        self._check_used_before_definition(node)
        self.generic_visit(node)

    def _check_division_by_zero(self, node: ast.BinOp):
        """Check for potential division by zero."""
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.issues.append(CodeIssue(
                    line=node.lineno, column=node.col_offset,
                    end_line=node.end_lineno or node.lineno,
                    end_column=node.end_col_offset or node.col_offset + 1,
                    severity=Severity.ERROR, code='E001',
                    message='Division by zero',
                    suggestion='Add a check: if divisor != 0',
                    fixable=False, category='bug'
                ))

    def _check_modulo_zero(self, node: ast.BinOp):
        """Check for potential modulo by zero."""
        if isinstance(node.op, ast.Mod):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.issues.append(CodeIssue(
                    line=node.lineno, column=node.col_offset,
                    end_line=node.end_lineno or node.lineno,
                    end_column=node.end_col_offset or node.col_offset + 1,
                    severity=Severity.ERROR, code='E002',
                    message='Modulo by zero',
                    suggestion='Add a check: if divisor != 0',
                    fixable=False, category='bug'
                ))

    def _check_infinite_loop(self, node: ast.While):
        """Check for while True without break."""
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_break = any(
                isinstance(n, ast.Break) for n in ast.walk(node)
            )
            if not has_break:
                self.issues.append(CodeIssue(
                    line=node.lineno, column=node.col_offset,
                    end_line=node.end_lineno or node.lineno,
                    end_column=node.end_col_offset or node.col_offset + 5,
                    severity=Severity.WARNING, code='W001',
                    message='Infinite loop: while True without break',
                    suggestion='Add a break condition or use a finite loop',
                    fixable=False, category='bug'
                ))

    def _check_unbounded_loop(self, node: ast.For):
        """Check for for loops with large ranges."""
        if isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                if len(node.iter.args) >= 1:
                    arg = node.iter.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                        if arg.value > 1000000:
                            self.issues.append(CodeIssue(
                                line=node.lineno, column=node.col_offset,
                                end_line=node.end_lineno or node.lineno,
                                end_column=node.end_col_offset or node.col_offset + 3,
                                severity=Severity.WARNING, code='W002',
                                message=f'Loop with {arg.value:,} iterations may be slow',
                                suggestion='Consider using batch processing or generators',
                                fixable=False, category='performance'
                            ))

    def _check_chained_comparison(self, node: ast.Compare):
        """Check for incorrect chained comparisons."""
        if len(node.ops) > 1:
            # x < y < z is fine, but x < y > z is suspicious
            ops = [type(op) for op in node.ops]
            if ast.Lt in ops and ast.Gt in ops:
                self.issues.append(CodeIssue(
                    line=node.lineno, column=node.col_offset,
                    end_line=node.end_lineno or node.lineno,
                    end_column=node.end_col_offset or node.col_offset + 1,
                    severity=Severity.WARNING, code='W003',
                    message='Mixed comparison operators in chain',
                    suggestion='This may not behave as expected. Use separate conditions.',
                    fixable=False, category='bug'
                ))

    def _check_bare_except(self, node: ast.ExceptHandler):
        """Check for bare except clauses."""
        if node.type is None:
            self.issues.append(CodeIssue(
                line=node.lineno, column=node.col_offset,
                end_line=node.end_lineno or node.lineno,
                end_column=node.end_col_offset or node.col_offset + 6,
                severity=Severity.WARNING, code='W004',
                message='Bare except catches all exceptions including SystemExit',
                suggestion='Use except Exception: or except SpecificError:',
                fixable=True, category='style'
            ))

    def _check_bare_except_in_call(self, node: ast.Call):
        """Check for potential issues in function calls."""
        pass

    def _check_mutable_default(self, node: ast.Call):
        """Check for mutable default arguments."""
        pass

    def _check_return_in_loop(self, node: ast.Return):
        """Check for return inside loop (may skip cleanup)."""
        pass

    def _check_unused_assignment(self, node: ast.Assign):
        """Check for variable assigned but never used."""
        pass

    def _check_self_assignment(self, node: ast.AugAssign):
        """Check for x = x + something pattern that could be simplified."""
        pass

    def _check_index_out_of_range(self, node: ast.Subscript):
        """Check for potential index out of range."""
        pass

    def _check_used_before_definition(self, node: ast.Name):
        """Check for variable used before definition."""
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Complexity Analysis
# ══════════════════════════════════════════════════════════════════════════════

class ComplexityAnalyzer(ast.NodeVisitor):
    """Calculates code complexity metrics."""

    def __init__(self):
        self.cyclomatic = 1
        self.cognitive = 0
        self._nesting = 0
        self._function_lengths: List[int] = []
        self._class_count = 0
        self._function_count = 0
        self._current_func_lines = 0
        self._operators: Dict[str, int] = {}
        self._operands: Dict[str, int] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._function_count += 1
        start = node.lineno
        end = node.end_lineno or node.lineno
        self._function_lengths.append(end - start + 1)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        self._class_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self.cyclomatic += 1
        self.cognitive += 1 + self._nesting
        self._nesting += 1
        self.generic_visit(node)
        self._nesting -= 1

    def visit_For(self, node):
        self.cyclomatic += 1
        self.cognitive += 1 + self._nesting
        self._nesting += 1
        self.generic_visit(node)
        self._nesting -= 1

    visit_AsyncFor = visit_For

    def visit_While(self, node):
        self.cyclomatic += 1
        self.cognitive += 1 + self._nesting
        self._nesting += 1
        self.generic_visit(node)
        self._nesting -= 1

    def visit_ExceptHandler(self, node):
        self.cyclomatic += 1
        self.cognitive += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Each boolean operator adds a branch (and/or)
        self.cyclomatic += len(node.values) - 1
        op_name = type(node.op).__name__
        self._operators[op_name] = self._operators.get(op_name, 0) + 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        self.cyclomatic += 1
        self.generic_visit(node)

    def visit_Await(self, node):
        self.cyclomatic += 1
        self.generic_visit(node)

    def visit_Yield(self, node):
        self.cyclomatic += 1
        self.generic_visit(node)

    def visit_YieldFrom(self, node):
        self.cyclomatic += 1
        self.generic_visit(node)

    def visit_BinOp(self, node):
        op_name = type(node.op).__name__
        self._operators[op_name] = self._operators.get(op_name, 0) + 1
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        op_name = type(node.op).__name__
        self._operators[op_name] = self._operators.get(op_name, 0) + 1
        self.generic_visit(node)

    def visit_Constant(self, node):
        key = str(node.value)[:50]
        self._operands[key] = self._operands.get(key, 0) + 1
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self._operands[node.id] = self._operands.get(node.id, 0) + 1
        self.generic_visit(node)

    def get_metrics(self, source_lines: List[str]) -> ComplexityMetrics:
        """Calculate all metrics from the analyzed AST."""
        metrics = ComplexityMetrics()
        metrics.cyclomatic = self.cyclomatic
        metrics.cognitive = self.cognitive
        metrics.functions = self._function_count
        metrics.classes = self._class_count
        metrics.lines_of_code = len(source_lines)
        metrics.max_depth = self._nesting

        if self._function_lengths:
            metrics.avg_function_length = sum(self._function_lengths) / len(self._function_lengths)

        # Count line types
        for line in source_lines:
            stripped = line.strip()
            if not stripped:
                metrics.blank_lines += 1
            elif stripped.startswith('#'):
                metrics.comment_lines += 1
            else:
                metrics.logical_lines += 1

        # Halstead metrics
        n_operators = sum(self._operators.values())
        n_operands = sum(self._operands.values())
        n1 = len(self._operators)
        n2 = len(self._operands)
        N = n_operators + n_operands

        if n1 > 0 and n2 > 0:
            metrics.halstead_volume = N * math.log2(n1 + n2) if (n1 + n2) > 1 else 0

        # Maintainability index (simplified)
        if metrics.logical_lines > 0:
            metrics.maintainability_index = max(0, min(100,
                171 - 5.2 * math.log(max(metrics.halstead_volume, 1))
                - 0.23 * metrics.cyclomatic
                - 16.2 * math.log(metrics.logical_lines)
            ))

        return metrics


# ══════════════════════════════════════════════════════════════════════════════
# Dead Code Detection
# ══════════════════════════════════════════════════════════════════════════════

class DeadCodeDetector(ast.NodeVisitor):
    """Detects unreachable or unused code."""

    def __init__(self):
        self.issues: List[CodeIssue] = []
        self._defined_names: Dict[str, int] = {}  # name -> line
        self._used_names: set = set()
        self._in_function = False
        self._after_return = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._defined_names[node.name] = node.lineno
        old_in_func = self._in_function
        self._in_function = True
        self._after_return = False
        self.generic_visit(node)
        self._in_function = old_in_func

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        self._defined_names[node.name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self._used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            if node.id not in self._defined_names:
                self._defined_names[node.id] = node.lineno
        self.generic_visit(node)

    def visit_Assign(self, node):
        if self._in_function and self._after_return:
            self.issues.append(CodeIssue(
                line=node.lineno, column=node.col_offset,
                end_line=node.end_lineno or node.lineno,
                end_column=node.end_col_offset or node.col_offset + 1,
                severity=Severity.WARNING, code='W010',
                message='Unreachable code after return statement',
                suggestion='Remove dead code or fix control flow',
                fixable=True, category='dead_code'
            ))
        self.generic_visit(node)

    def visit_Return(self, node):
        self._after_return = True
        self.generic_visit(node)

    def get_unused_definitions(self) -> List[CodeIssue]:
        """Find defined but unused names (excluding private and dunder)."""
        unused = []
        for name, line in self._defined_names.items():
            if name.startswith('_'):
                continue
            if name in ('main', '__init__', '__str__', '__repr__'):
                continue
            if name not in self._used_names:
                unused.append(CodeIssue(
                    line=line, column=0, end_line=line, end_column=len(name),
                    severity=Severity.INFO, code='I001',
                    message=f"'{name}' is defined but never used",
                    suggestion=f"Remove '{name}' or use it somewhere",
                    fixable=True, category='dead_code'
                ))
        return unused


# ══════════════════════════════════════════════════════════════════════════════
# Refactoring Suggestions
# ══════════════════════════════════════════════════════════════════════════════

class RefactoringDetector(ast.NodeVisitor):
    """Detects refactoring opportunities."""

    def __init__(self):
        self.issues: List[CodeIssue] = []
        self._function_bodies: Dict[str, List[str]] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_long_function(node)
        self._check_too_many_arguments(node)
        self._check_nested_functions(node)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        self._check_large_class(node)
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self._check_deeply_nested(node)
        self.generic_visit(node)

    def _check_long_function(self, node: ast.FunctionDef):
        """Suggest splitting long functions."""
        length = (node.end_lineno or node.lineno) - node.lineno
        if length > 50:
            self.issues.append(CodeIssue(
                line=node.lineno, column=node.col_offset,
                end_line=node.end_lineno or node.lineno,
                end_column=node.end_col_offset or node.col_offset + len(node.name),
                severity=Severity.INFO, code='R001',
                message=f"Function '{node.name}' is {length} lines long",
                suggestion='Consider splitting into smaller functions (max 50 lines)',
                fixable=False, category='refactor'
            ))

    def _check_too_many_arguments(self, node: ast.FunctionDef):
        """Suggest reducing function arguments."""
        args = len(node.args.args) + len(node.args.posonlyargs) + len(node.args.kwonlyargs)
        if args > 5:
            self.issues.append(CodeIssue(
                line=node.lineno, column=node.col_offset,
                end_line=node.end_lineno or node.lineno,
                end_column=node.end_col_offset or node.col_offset + len(node.name),
                severity=Severity.INFO, code='R002',
                message=f"Function '{node.name}' has {args} arguments",
                suggestion='Consider using a dataclass or config object for many parameters',
                fixable=False, category='refactor'
            ))

    def _check_nested_functions(self, node: ast.FunctionDef):
        """Detect nested function definitions."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.issues.append(CodeIssue(
                    line=child.lineno, column=child.col_offset,
                    end_line=child.end_lineno or child.lineno,
                    end_column=child.end_col_offset or child.col_offset + len(child.name),
                    severity=Severity.INFO, code='R003',
                    message=f"Nested function '{child.name}' inside '{node.name}'",
                    suggestion='Consider extracting to a separate function unless closure is needed',
                    fixable=False, category='refactor'
                ))

    def _check_large_class(self, node: ast.ClassDef):
        """Suggest splitting large classes."""
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if len(methods) > 15:
            self.issues.append(CodeIssue(
                line=node.lineno, column=node.col_offset,
                end_line=node.end_lineno or node.lineno,
                end_column=node.end_col_offset or node.col_offset + len(node.name),
                severity=Severity.INFO, code='R004',
                message=f"Class '{node.name}' has {len(methods)} methods",
                suggestion='Consider splitting into smaller classes (Single Responsibility Principle)',
                fixable=False, category='refactor'
            ))

    def _check_deeply_nested(self, node: ast.If):
        """Detect deeply nested if statements."""
        depth = self._count_nesting(node)
        if depth > 4:
            self.issues.append(CodeIssue(
                line=node.lineno, column=node.col_offset,
                end_line=node.end_lineno or node.lineno,
                end_column=node.end_col_offset or node.col_offset + 2,
                severity=Severity.INFO, code='R005',
                message=f'Nesting depth of {depth} is too high',
                suggestion='Use early returns, guard clauses, or extract to functions',
                fixable=False, category='refactor'
            ))

    def _count_nesting(self, node, depth=0) -> int:
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                child_depth = self._count_nesting(child, depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth


# ══════════════════════════════════════════════════════════════════════════════
# Import Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class ImportAnalyzer(ast.NodeVisitor):
    """Analyzes imports and detects issues."""

    def __init__(self):
        self.issues: List[CodeIssue] = []
        self.imports: List[str] = []
        self._imported_names: Dict[str, int] = {}  # name -> line

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.append(alias.name)
            self._imported_names[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ''
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.append(f"{module}.{alias.name}")
            self._imported_names[name] = node.lineno
        self.generic_visit(node)

    def get_unused_imports(self, used_names: set) -> List[CodeIssue]:
        """Find imported but unused names."""
        unused = []
        for name, line in self._imported_names.items():
            if name not in used_names and name != '*':
                unused.append(CodeIssue(
                    line=line, column=0, end_line=line, end_column=len(name),
                    severity=Severity.WARNING, code='W020',
                    message=f"Unused import: '{name}'",
                    suggestion=f"Remove 'import {name}' or use it",
                    fixable=True, category='style'
                ))
        return unused


# ══════════════════════════════════════════════════════════════════════════════
# Main Parser - Ties Everything Together
# ══════════════════════════════════════════════════════════════════════════════

class PythonParser:
    """
    Main Python AST parser for NexusIDE.
    Runs all analyzers and returns a comprehensive result.
    """

    def analyze(self, code: str) -> AnalysisResult:
        """
        Analyze Python code and return comprehensive results.
        
        Args:
            code: Python source code string
            
        Returns:
            AnalysisResult with issues, metrics, dependencies, exports
        """
        result = AnalysisResult()

        if not code or not code.strip():
            return result

        source_lines = code.split('\n')

        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.ast_valid = False
            result.parse_error = f"Syntax error at line {e.lineno}: {e.msg}"
            result.issues.append(CodeIssue(
                line=e.lineno or 1, column=e.offset or 0,
                end_line=e.lineno or 1, end_column=(e.offset or 0) + 1,
                severity=Severity.ERROR, code='E010',
                message=f"Syntax error: {e.msg}",
                suggestion='Fix the syntax error',
                fixable=False, category='syntax'
            ))
            return result

        # Run all analyzers
        try:
            # Bug detection
            bug_detector = BugDetector()
            bug_detector.visit(tree)
            result.issues.extend(bug_detector.issues)

            # Complexity analysis
            complexity = ComplexityAnalyzer()
            complexity.visit(tree)
            result.metrics = complexity.get_metrics(source_lines)

            # Dead code detection
            dead_code = DeadCodeDetector()
            dead_code.visit(tree)
            result.issues.extend(dead_code.get_unused_definitions())
            result.issues.extend(dead_code.issues)

            # Refactoring suggestions
            refactoring = RefactoringDetector()
            refactoring.visit(tree)
            result.issues.extend(refactoring.issues)

            # Import analysis
            import_analyzer = ImportAnalyzer()
            import_analyzer.visit(tree)

            # Collect all used names
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)

            result.issues.extend(import_analyzer.get_unused_imports(used_names))
            result.dependencies = import_analyzer.imports

            # Find exports (public names)
            result.exports = self._find_exports(tree)

            # Sort issues by line number
            result.issues.sort(key=lambda x: (x.line, x.column))

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            result.issues.append(CodeIssue(
                line=1, column=0, end_line=1, end_column=1,
                severity=Severity.ERROR, code='E999',
                message=f'Analysis failed: {str(e)}',
                fixable=False, category='system'
            ))

        return result

    def _find_exports(self, tree: ast.AST) -> List[str]:
        """Find all public names (not starting with _)."""
        exports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):
                    exports.append(node.name)
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith('_'):
                    exports.append(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith('_'):
                        exports.append(target.id)
        return exports

    def analyze_line(self, code: str, line_number: int) -> List[CodeIssue]:
        """Analyze a specific line for inline suggestions."""
        result = self.analyze(code)
        return [issue for issue in result.issues if issue.line == line_number]


# Singleton
_parser = None


def get_parser() -> PythonParser:
    """Get the Python parser instance."""
    global _parser
    if _parser is None:
        _parser = PythonParser()
    return _parser


def analyze_python_code(code: str) -> AnalysisResult:
    """Quick analysis of Python code."""
    return get_parser().analyze(code)
