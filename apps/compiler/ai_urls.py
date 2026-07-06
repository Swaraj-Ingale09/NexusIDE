from django.urls import path
from . import ai_views

app_name = 'ai'

urlpatterns = [
    # Streaming endpoint
    path('stream/', ai_views.AIStreamView.as_view(), name='stream'),

    # Main AI endpoint (all in one)
    path('assistant/', ai_views.AIAssistantView.as_view(), name='assistant'),
    
    # Specific AI features
    path('fix/', ai_views.AutoFixView.as_view(), name='auto-fix'),
    path('optimize/', ai_views.CodeOptimizationView.as_view(), name='optimize'),
    path('explain/', ai_views.CodeExplanationView.as_view(), name='explain'),
    path('test/', ai_views.TestGenerationView.as_view(), name='generate-tests'),
    path('refactor/', ai_views.CodeRefactoringView.as_view(), name='refactor'),
    path('review/', ai_views.CodeReviewView.as_view(), name='review'),
    path('debug/', ai_views.CodeDebugView.as_view(), name='debug'),
    
    # Chat
    path('chat/', ai_views.AIChatView.as_view(), name='chat'),
]
