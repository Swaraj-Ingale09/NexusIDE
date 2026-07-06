"""
In-Line Suggestions URL Routes
Fast endpoints using OpenRouter & Nvidia NIM
"""

from django.urls import path
from apps.compiler import suggestions_api

app_name = 'suggestions'

urlpatterns = [
    # Quick APIs - Super fast, real-time
    path('quick-fix/', suggestions_api.quick_fix_api, name='quick-fix'),
    path('quick-explain/', suggestions_api.quick_explain_api, name='quick-explain'),
    path('quick-optimize/', suggestions_api.quick_optimize_api, name='quick-optimize'),
    path('quick-review/', suggestions_api.quick_review_api, name='quick-review'),
    path('quick-suggest/', suggestions_api.quick_suggest_api, name='quick-suggest'),
    
    # Code generation - ChatGPT-like
    path('generate/', suggestions_api.generate_code_api, name='generate'),
    
    # Smart suggestions - Rules + AI
    path('smart/', suggestions_api.smart_suggestions_api, name='smart'),
    
    # Complete assistant
    path('assistant/', suggestions_api.CodeAssistantView.as_view(), name='assistant'),
]
