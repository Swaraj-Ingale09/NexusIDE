"""
Working Email Backend - Direct SMTP with better error handling
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings


class WorkingEmailBackend:
    """
    Direct SMTP backend that actually sends emails
    Uses standard Python smtplib with Brevo
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently
    
    def send_messages(self, email_messages):
        """Send email messages"""
        if not email_messages:
            return 0
        
        msg_count = 0
        
        for message in email_messages:
            try:
                # Create SMTP connection
                smtp = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                smtp.starttls()
                
                # Login
                smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                
                # Send email
                smtp.send_message(message)
                smtp.quit()
                
                print(f"[EMAIL] ✓ Sent to {', '.join(message.to)}")
                msg_count += 1
                
            except smtplib.SMTPAuthenticationError as e:
                print(f"[EMAIL] ✗ Auth Error: {str(e)}")
                if not self.fail_silently:
                    raise
            except Exception as e:
                print(f"[EMAIL] ✗ Error: {type(e).__name__}: {str(e)}")
                if not self.fail_silently:
                    raise
        
        return msg_count
    
    def close(self):
        pass
