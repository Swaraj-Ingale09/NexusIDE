"""
SQL AI Assistant - Dedicated AI endpoint for SQL queries.
Provides Generate, Explain, Optimize, Fix, and Chat actions
with full database schema context.
"""

import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .prompt_guard import get_injection_protector

logger = logging.getLogger(__name__)
_injection_protector = get_injection_protector()

SCHEMA_CONTEXT = """Database Schema:
- Customers (CustomerID INTEGER PK, CustomerName TEXT, ContactName TEXT, City TEXT, Country TEXT) — 10 rows
- Products (ProductID INTEGER PK AUTOINCREMENT, ProductName TEXT, Price REAL, Unit TEXT) — 10 rows
- Orders (OrderID INTEGER PK AUTOINCREMENT, CustomerID INTEGER FK→Customers, ProductID INTEGER FK→Products, Quantity INTEGER, OrderDate TEXT) — 10 rows"""


def _build_sql_prompt(action, query, user_message='', error='', output=''):
    """Build SQL-specific prompts with schema context."""
    base = f"{SCHEMA_CONTEXT}\n\n"

    prompts = {
        'generate': (
            f"{base}Generate a SQL query based on this request:\n{user_message}\n\n"
            "Return ONLY the SQL query in a code block like ```sql ... ```. "
            "No explanation outside the code block."
        ),
        'explain': (
            f"{base}Explain what this SQL query does step by step:\n\n```sql\n{query}\n```\n\n"
            "Cover: what tables it touches, JOINs, WHERE conditions, aggregates, and the expected result set."
        ),
        'optimize': (
            f"{base}Optimize this SQL query for better performance. Suggest indexes if needed:\n\n```sql\n{query}\n```\n\n"
            "Return the optimized SQL in a ```sql ... ``` code block, then explain your changes."
        ),
        'fix': (
            f"{base}Fix this SQL query that has an error:\n\n```sql\n{query}\n```\n\n"
            f"{('Error: ' + error) if error else ''}\n\n"
            "Return the corrected SQL in a ```sql ... ``` code block, then explain what was wrong."
        ),
        'chat': (
            f"{base}"
            f"{'Current query:\n```sql\n' + query + '\n```\n\n' if query.strip() else ''}"
            f"User question: {user_message}\n\n"
            "Answer concisely. If the answer involves SQL, use ```sql ... ``` code blocks."
        ),
    }

    return prompts.get(action, prompts['chat'])


@method_decorator(csrf_exempt, name='dispatch')
class SQLAIView(APIView):
    """
    SQL AI Assistant endpoint.
    POST /api/sql-ai/
    Body: { action, query, message, error, output }
    Returns SSE stream: data: <chunk>\\n\\n ... data: [DONE]\\n\\n
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            body = request.data

        action = body.get('action', 'chat').lower()
        query = body.get('query', '').strip()
        user_message = body.get('message', '').strip()
        error = body.get('error', '')
        output = body.get('output', '')

        if not query and action != 'generate' and action != 'chat':
            return Response({'error': 'SQL query is required'}, status=400)

        if not user_message and action == 'chat':
            return Response({'error': 'Message is required'}, status=400)

        if not user_message and action == 'generate':
            return Response({'error': 'Description is required for generation'}, status=400)

        # Prompt injection protection
        if user_message:
            safe, is_suspicious, reason = _injection_protector.sanitize_for_ai(
                user_message, code_context=query
            )
            if is_suspicious:
                logger.warning("SQL AI prompt injection blocked: %s", reason)
                user_message = safe

        prompt = _build_sql_prompt(action, query, user_message, error, output)

        def event_stream():
            try:
                from .ai_providers import get_multi_provider_ai
                ai = get_multi_provider_ai()

                # Try OpenRouter streaming first
                if ai.openrouter:
                    for chunk in ai.openrouter.stream(prompt, max_tokens=2048, temperature=0.5):
                        safe = chunk.replace('\n', '\\n')
                        yield f"data: {safe}\n\n"
                    return

                # Fallback: Groq non-streaming (send full response as one chunk)
                if ai.groq:
                    messages = [{"role": "user", "content": prompt}]
                    result = ai.groq._call(messages, max_tokens=2048, temperature=0.5)
                    if result:
                        safe = result.replace('\n', '\\n')
                        yield f"data: {safe}\n\n"
                        return

                yield "data: [ERROR] No AI provider available. Check GROQ_API_KEYS in .env\\n\n"
            except Exception as e:
                logger.exception("SQL AI error")
                yield f"data: [ERROR] {str(e)}\\n\n"
            finally:
                yield "data: [DONE]\n\n"

        from django.http import StreamingHttpResponse
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
