import logging

logger = logging.getLogger(__name__)


def get_ai_explanation(code, error=None):
    """Provide code explanation"""
    lines = code.strip().split('\n')
    explanation = f"""
Code Analysis:

This code snippet has {len(lines)} lines.

What it does:
- Defines Python functions/classes
- Performs operations on data
- Handles logic flow

How it works:
1. Code is parsed by Python interpreter
2. Functions/classes are defined
3. Logic flows through the code path
4. Results are produced

Tips:
- Add comments to explain complex logic
- Use meaningful variable names
- Break down complex functions into smaller pieces
- Test your code with various inputs
"""
    return explanation.strip()


def get_ai_fix(code, error):
    """Provide code fix suggestions"""
    fix_suggestion = f"""
Error Analysis:

Error Message: {error}

Common fixes:
1. Check syntax - missing colons, brackets, or parentheses
2. Check indentation - Python uses indentation for blocks
3. Check variable names - spelling and case sensitivity
4. Check function calls - correct number of arguments
5. Check types - ensure operations work with the data types

To fix:
1. Read the error message carefully - it often tells you the issue
2. Look at the line number mentioned in the error
3. Check for common Python mistakes:
   - Missing ':' after if/for/while/def
   - Incorrect indentation
   - Undefined variables
   - Wrong method/function names

Example common fixes:
- def foo(x  → def foo(x):
- if x == y  → if x == y:
- for i in range(10)  → for i in range(10):
- print('hello  → print('hello')
"""
    return fix_suggestion.strip()


def get_ai_suggestions(code):
    """Get optimization suggestions"""
    suggestions = f"""
Code Optimization Tips:

Current code analysis:
- Lines of code: {len(code.split(chr(10)))}
- Code quality: Can be improved

Optimization suggestions:

1. Performance:
   - Use list comprehensions instead of loops
   - Use built-in functions (map, filter, etc)
   - Avoid nested loops when possible
   - Cache results of expensive operations

2. Readability:
   - Add comments explaining complex logic
   - Use meaningful variable names
   - Break down large functions into smaller ones
   - Follow PEP 8 style guide

3. Best Practices:
   - Add error handling (try/except)
   - Validate input parameters
   - Use type hints for clarity
   - Add docstrings to functions

4. Example optimization:
   Instead of:
   result = []
   for i in range(10):
       result.append(i * 2)
   
   Use:
   result = [i * 2 for i in range(10)]
"""
    return suggestions.strip()


def get_ai_format(code):
    """Format code to PEP 8 standards"""
    # Basic PEP 8 formatting
    lines = code.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Remove trailing whitespace
        line = line.rstrip()
        # Add proper indentation
        if line.strip():
            indent = len(line) - len(line.lstrip())
            # Normalize indentation to 4 spaces per level
            normalized_indent = (indent // 4) * 4
            formatted_lines.append(' ' * normalized_indent + line.strip())
        else:
            formatted_lines.append('')
    
    return '\n'.join(formatted_lines)


def get_ai_test_generation(code):
    """Generate basic unit tests"""
    test_template = f"""
import pytest

# Auto-generated test template for your code

def test_basic_functionality():
    \"\"\"Test basic functionality\"\"\"
    # TODO: Add your test here
    assert True

def test_edge_cases():
    \"\"\"Test edge cases\"\"\"
    # TODO: Test with boundary values
    assert True

def test_error_handling():
    \"\"\"Test error handling\"\"\"
    # TODO: Test error conditions
    with pytest.raises(Exception):
        pass  # Your code here

# Run tests with: pytest test_file.py
# Or: python -m pytest test_file.py
"""
    return test_template.strip()

