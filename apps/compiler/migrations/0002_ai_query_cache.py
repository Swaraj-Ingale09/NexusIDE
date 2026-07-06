# Generated migration for AIQuery and AIQueryCache models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('compiler', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AIQuery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('fix', 'Fix Code'), ('explain', 'Explain Code'), ('optimize', 'Optimize Code'), ('review', 'Review Code'), ('suggest', 'Suggest Improvements'), ('generate', 'Generate Code'), ('chat', 'Chat')], max_length=20)),
                ('query_input', models.TextField()),
                ('query_hash', models.CharField(db_index=True, max_length=64)),
                ('response_output', models.TextField()),
                ('provider', models.CharField(default='openrouter', max_length=50)),
                ('status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('partial', 'Partial Success')], default='success', max_length=20)),
                ('execution_time', models.FloatField(default=0)),
                ('model_name', models.CharField(blank=True, max_length=100)),
                ('tokens_used', models.IntegerField(default=0)),
                ('error_message', models.TextField(blank=True)),
                ('reuse_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code_snippet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_queries', to='compiler.codesnippet')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ai_queries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'ai_queries',
            },
        ),
        migrations.CreateModel(
            name='AIQueryCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query_hash', models.CharField(db_index=True, max_length=64, unique=True)),
                ('action', models.CharField(max_length=20)),
                ('cached_response', models.TextField()),
                ('cached_provider', models.CharField(max_length=50)),
                ('hit_count', models.IntegerField(default=1)),
                ('last_hit', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'ai_query_cache',
            },
        ),
        migrations.AddIndex(
            model_name='aiquery',
            index=models.Index(fields=['user', '-created_at'], name='compiler_aiquery_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='aiquery',
            index=models.Index(fields=['query_hash'], name='compiler_aiquery_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='aiquery',
            index=models.Index(fields=['action', 'status'], name='compiler_aiquery_action_status_idx'),
        ),
        migrations.AddIndex(
            model_name='aiquery',
            index=models.Index(fields=['provider'], name='compiler_aiquery_provider_idx'),
        ),
    ]
