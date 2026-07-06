# Add database indexes for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_useractivity_activity_type_userheartbeat'),
    ]

    operations = [
        # Add indexes to UserHeartbeat for common queries
        migrations.AddIndex(
            model_name='userheartbeat',
            index=models.Index(fields=['user', '-timestamp'], name='user_heartbeat_idx'),
        ),
        migrations.AddIndex(
            model_name='userheartbeat',
            index=models.Index(fields=['timestamp'], name='heartbeat_timestamp_idx'),
        ),
        
        # Add indexes to UserActivity
        migrations.AddIndex(
            model_name='useractivity',
            index=models.Index(fields=['user', '-timestamp'], name='user_activity_idx'),
        ),
        migrations.AddIndex(
            model_name='useractivity',
            index=models.Index(fields=['-timestamp'], name='activity_timestamp_idx'),
        ),
        
        # Add indexes to UserSession
        migrations.AddIndex(
            model_name='usersession',
            index=models.Index(fields=['user', '-login_time'], name='user_session_idx'),
        ),
        
        # Add index to UserProfile
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['email_verified'], name='email_verified_idx'),
        ),
    ]
