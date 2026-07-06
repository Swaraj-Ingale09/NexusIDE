"""
Tests for the Python AST parser.
Covers bug detection, complexity analysis, dead code detection, and refactoring suggestions.
"""
from django.test import TestCase
from apps.compiler.python_parser import (
    PythonParser, BugDetector, ComplexityAnalyzer,
    DeadCodeDetector, RefactoringDetector, ImportAnalyzer,
    analyze_python_code, Severity
)


class TestSyntaxErrors(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_invalid_syntax(self):
        result = self.parser.analyze("def foo(")
        self.assertFalse(result.ast_valid)
        self.assertIsNotNone(result.parse_error)
        self.assertIn('Syntax error', result.parse_error)
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].severity, Severity.ERROR)
        self.assertEqual(result.issues[0].code, 'E010')

    def test_empty_code(self):
        result = self.parser.analyze("")
        self.assertTrue(result.ast_valid)
        self.assertEqual(len(result.issues), 0)

    def test_valid_code(self):
        result = self.parser.analyze("x = 1\nprint(x)")
        self.assertTrue(result.ast_valid)
        self.assertIsNone(result.parse_error)


class TestBugDetection(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_division_by_zero(self):
        code = "x = 1 / 0"
        result = self.parser.analyze(code)
        errors = [i for i in result.issues if i.code == 'E001']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].severity, Severity.ERROR)
        self.assertEqual(errors[0].category, 'bug')

    def test_floor_division_by_zero(self):
        code = "x = 10 // 0"
        result = self.parser.analyze(code)
        errors = [i for i in result.issues if i.code == 'E001']
        self.assertEqual(len(errors), 1)

    def test_modulo_by_zero(self):
        code = "x = 10 % 0"
        result = self.parser.analyze(code)
        errors = [i for i in result.issues if i.code == 'E002']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].severity, Severity.ERROR)

    def test_no_division_by_zero_in_variable(self):
        code = "y = 0\nx = 1 / y"
        result = self.parser.analyze(code)
        errors = [i for i in result.issues if i.code == 'E001']
        self.assertEqual(len(errors), 0)

    def test_infinite_loop(self):
        code = "while True:\n    pass"
        result = self.parser.analyze(code)
        warnings = [i for i in result.issues if i.code == 'W001']
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].severity, Severity.WARNING)
        self.assertEqual(warnings[0].category, 'bug')

    def test_infinite_loop_with_break(self):
        code = "while True:\n    break"
        result = self.parser.analyze(code)
        warnings = [i for i in result.issues if i.code == 'W001']
        self.assertEqual(len(warnings), 0)

    def test_bare_except(self):
        code = "try:\n    pass\nexcept:\n    pass"
        result = self.parser.analyze(code)
        warnings = [i for i in result.issues if i.code == 'W004']
        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0].fixable)

    def test_no_bare_except_with_exception(self):
        code = "try:\n    pass\nexcept Exception:\n    pass"
        result = self.parser.analyze(code)
        warnings = [i for i in result.issues if i.code == 'W004']
        self.assertEqual(len(warnings), 0)

    def test_large_loop(self):
        code = "for i in range(2000000):\n    pass"
        result = self.parser.analyze(code)
        warnings = [i for i in result.issues if i.code == 'W002']
        self.assertEqual(len(warnings), 1)
        self.assertIn('2,000,000', warnings[0].message)


class TestComplexityAnalysis(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_simple_function(self):
        code = "def foo():\n    return 1"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.cyclomatic, 1)
        self.assertEqual(result.metrics.functions, 1)

    def test_if_branches(self):
        code = "if x:\n    pass\nelif y:\n    pass\nelse:\n    pass"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.cyclomatic, 3)

    def test_for_loop(self):
        code = "for i in range(10):\n    pass"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.cyclomatic, 2)

    def test_while_loop(self):
        code = "while x > 0:\n    pass"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.cyclomatic, 2)

    def test_boolean_operators(self):
        code = "if a and b or c:\n    pass"
        result = self.parser.analyze(code)
        self.assertGreaterEqual(result.metrics.cyclomatic, 3)

    def test_try_except(self):
        code = "try:\n    pass\nexcept:\n    pass"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.cyclomatic, 2)

    def test_ternary(self):
        code = "x = 1 if True else 0"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.cyclomatic, 2)

    def test_class_count(self):
        code = "class Foo:\n    pass\nclass Bar:\n    pass"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.classes, 2)

    def test_lines_of_code(self):
        code = "x = 1\ny = 2\n\n# comment\nz = 3"
        result = self.parser.analyze(code)
        self.assertEqual(result.metrics.lines_of_code, 5)
        self.assertEqual(result.metrics.blank_lines, 1)
        self.assertEqual(result.metrics.comment_lines, 1)

    def test_halstead_volume(self):
        code = "x = a + b * c"
        result = self.parser.analyze(code)
        self.assertGreater(result.metrics.halstead_volume, 0)

    def test_maintainability_index(self):
        code = "def simple():\n    return 1"
        result = self.parser.analyze(code)
        self.assertGreaterEqual(result.metrics.maintainability_index, 0)
        self.assertLessEqual(result.metrics.maintainability_index, 100)


class TestDeadCodeDetection(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_unreachable_after_return(self):
        code = "def foo():\n    return 1\n    x = 2"
        result = self.parser.analyze(code)
        dead = [i for i in result.issues if i.code == 'W010']
        self.assertEqual(len(dead), 1)
        self.assertEqual(dead[0].category, 'dead_code')

    def test_no_dead_code_normal(self):
        code = "def foo():\n    x = 1\n    return x"
        result = self.parser.analyze(code)
        dead = [i for i in result.issues if i.code == 'W010']
        self.assertEqual(len(dead), 0)


class TestRefactoringSuggestions(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_long_function(self):
        lines = ["def foo():"] + ["    x = 1"] * 55
        code = "\n".join(lines)
        result = self.parser.analyze(code)
        refactor = [i for i in result.issues if i.code == 'R001']
        self.assertEqual(len(refactor), 1)
        self.assertIn('55 lines', refactor[0].message)

    def test_too_many_arguments(self):
        code = "def foo(a, b, c, d, e, f):\n    pass"
        result = self.parser.analyze(code)
        refactor = [i for i in result.issues if i.code == 'R002']
        self.assertEqual(len(refactor), 1)

    def test_nested_function(self):
        code = "def outer():\n    def inner():\n        pass"
        result = self.parser.analyze(code)
        refactor = [i for i in result.issues if i.code == 'R003']
        self.assertEqual(len(refactor), 1)

    def test_large_class(self):
        methods = "\n".join([f"    def method{i}(self): pass" for i in range(20)])
        code = f"class Big:\n{methods}"
        result = self.parser.analyze(code)
        refactor = [i for i in result.issues if i.code == 'R004']
        self.assertEqual(len(refactor), 1)

    def test_no_refactor_small(self):
        code = "def foo():\n    return 1"
        result = self.parser.analyze(code)
        refactor = [i for i in result.issues if i.code.startswith('R')]
        self.assertEqual(len(refactor), 0)


class TestImportAnalysis(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_unused_import(self):
        code = "import os\nx = 1"
        result = self.parser.analyze(code)
        unused = [i for i in result.issues if i.code == 'W020']
        self.assertEqual(len(unused), 1)
        self.assertIn('os', unused[0].message)

    def test_used_import(self):
        code = "import os\nos.getcwd()"
        result = self.parser.analyze(code)
        unused = [i for i in result.issues if i.code == 'W020']
        self.assertEqual(len(unused), 0)

    def test_from_import(self):
        code = "from os import path\nx = 1"
        result = self.parser.analyze(code)
        unused = [i for i in result.issues if i.code == 'W020']
        self.assertEqual(len(unused), 1)

    def test_dependencies_tracked(self):
        code = "import os\nfrom sys import argv"
        result = self.parser.analyze(code)
        self.assertIn('os', result.dependencies)
        self.assertIn('sys.argv', result.dependencies)


class TestExports(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_public_functions(self):
        code = "def public():\n    pass\ndef _private():\n    pass"
        result = self.parser.analyze(code)
        self.assertIn('public', result.exports)
        self.assertNotIn('_private', result.exports)

    def test_public_classes(self):
        code = "class MyClass:\n    pass\nclass _Internal:\n    pass"
        result = self.parser.analyze(code)
        self.assertIn('MyClass', result.exports)
        self.assertNotIn('_Internal', result.exports)

    def test_public_variables(self):
        code = "PUBLIC = 1\n_PRIVATE = 2"
        result = self.parser.analyze(code)
        self.assertIn('PUBLIC', result.exports)
        self.assertNotIn('_PRIVATE', result.exports)


class TestEdgeCases(TestCase):
    def setUp(self):
        self.parser = PythonParser()

    def test_single_line(self):
        result = self.parser.analyze("x = 1")
        self.assertTrue(result.ast_valid)
        # x is defined but never used - valid warning
        self.assertEqual(len(result.issues), 1)
        self.assertEqual(result.issues[0].code, 'I001')

    def test_complex_code(self):
        code = '''
import os
import sys

class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(result)
        return result
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

def main():
    calc = Calculator()
    print(calc.add(1, 2))
    print(calc.divide(10, 2))

if __name__ == "__main__":
    main()
'''
        result = self.parser.analyze(code)
        self.assertTrue(result.ast_valid)
        self.assertGreaterEqual(result.metrics.functions, 3)
        self.assertEqual(result.metrics.classes, 1)

    def test_analyze_line(self):
        code = "x = 1\ny = 2\nz = 3"
        issues = self.parser.analyze_line(code, 2)
        for issue in issues:
            self.assertEqual(issue.line, 2)


class TestMetricsEndpoint(TestCase):
    def test_analyze_python_code(self):
        code = "def foo():\n    return 1"
        result = analyze_python_code(code)
        self.assertTrue(result.ast_valid)
        self.assertEqual(result.metrics.functions, 1)

    def test_to_dict(self):
        code = "x = 1 / 0"
        result = analyze_python_code(code)
        d = result.to_dict()
        self.assertIn('issues', d)
        self.assertIn('metrics', d)
        self.assertIn('astValid', d)
        self.assertTrue(d['astValid'])
        self.assertGreater(len(d['issues']), 0)


class TestIssueSerialization(TestCase):
    def test_issue_to_dict(self):
        code = "x = 1 / 0"
        result = analyze_python_code(code)
        # Find the division by zero error
        error_issues = [i for i in result.issues if i.code == 'E001']
        self.assertEqual(len(error_issues), 1)
        issue = error_issues[0]
        d = issue.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d['severity'], 'error')
        self.assertEqual(d['code'], 'E001')
        self.assertEqual(d['category'], 'bug')
        self.assertIsInstance(d['line'], int)
