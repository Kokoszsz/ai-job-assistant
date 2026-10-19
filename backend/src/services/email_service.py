"""
Email Service
=============
Send emails for password reset and notifications.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from typing import Optional


class EmailService:
    """Service for sending emails."""
    
    def __init__(self):
        """Initialize email service with Flask config."""
        self.server = None
    
    def _connect(self):
        """Connect to SMTP server."""
        if not self.server:
            self.server = smtplib.SMTP(
                current_app.config['MAIL_SERVER'],
                current_app.config['MAIL_PORT']
            )
            if current_app.config['MAIL_USE_TLS']:
                self.server.starttls()
            
            # Authenticate if credentials provided
            if current_app.config['MAIL_USERNAME'] and current_app.config['MAIL_PASSWORD']:
                self.server.login(
                    current_app.config['MAIL_USERNAME'],
                    current_app.config['MAIL_PASSWORD']
                )
    
    def _disconnect(self):
        """Disconnect from SMTP server."""
        if self.server:
            self.server.quit()
            self.server = None
    
    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None):
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body
        """
        try:
            self._connect()
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
            msg['To'] = to_email
            
            # Attach plain text
            msg.attach(MIMEText(body_text, 'plain'))
            
            # Attach HTML if provided
            if body_html:
                msg.attach(MIMEText(body_html, 'html'))
            
            self.server.sendmail(
                current_app.config['MAIL_DEFAULT_SENDER'],
                to_email,
                msg.as_string()
            )
            
            current_app.logger.info(f"Email sent to {to_email}: {subject}")
        
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise
        
        finally:
            self._disconnect()
    
    def send_password_reset_email(self, to_email: str, reset_token: str):
        """
        Send password reset email.
        
        Args:
            to_email: User's email address
            reset_token: Password reset token
        """
        # Construct reset URL (in production, use proper frontend URL)
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"
        
        subject = "Password Reset Request"
        
        body_text = f"""
Hello,

You requested a password reset for your AI Job Search Assistant account.

Click the link below to reset your password (link expires in 1 hour):

{reset_url}

If you did not request this reset, please ignore this email.

Best regards,
AI Job Search Assistant Team
"""
        
        body_html = f"""
<html>
<body>
    <h2>Password Reset Request</h2>
    <p>Hello,</p>
    <p>You requested a password reset for your AI Job Search Assistant account.</p>
    <p>
        <a href="{reset_url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
            Reset Password
        </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p><em>This link expires in 1 hour.</em></p>
    <p>If you did not request this reset, please ignore this email.</p>
    <br>
    <p>Best regards,<br>AI Job Search Assistant Team</p>
</body>
</html>
"""
        
        self.send_email(to_email, subject, body_text, body_html)
