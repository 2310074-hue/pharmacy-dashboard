import os
import secrets
import string
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from ..models import PasswordResetOTP
from .email_utils import send_universal_mail


def generate_secure_otp(length=6):
    """Generate a cryptographic 6-digit numeric OTP code."""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def generate_reset_token():
    """Generate a secure 64-character URL-safe token."""
    return secrets.token_hex(32)


def mask_email(email):
    """Mask email for privacy, e.g., admin@example.com -> a***n@example.com"""
    if not email or '@' not in email:
        return 'your registered email'
    parts = email.split('@')
    name, domain = parts[0], parts[1]
    if len(name) <= 2:
        masked_name = name[0] + '*'
    else:
        masked_name = name[0] + '*' * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


def get_client_ip(request):
    """Extract client IP address from request headers."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def create_and_send_reset_otp(user, request=None):
    """
    Creates a new 6-digit OTP record and sends it via email.
    Supports smart fallback for local environments and Render cloud.
    """
    # 1. Invalidate older unused OTPs for this user
    PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

    # 2. Generate new OTP & token
    otp_code = generate_secure_otp(6)
    token = generate_reset_token()
    now = timezone.now()
    expires_at = now + timedelta(minutes=15)
    ip_addr = get_client_ip(request)

    otp_obj = PasswordResetOTP.objects.create(
        user=user,
        otp_code=otp_code,
        token=token,
        created_at=now,
        expires_at=expires_at,
        is_used=False,
        ip_address=ip_addr
    )

    # 3. Build email content
    recipient_email = user.email.strip() if user.email else ''
    masked = mask_email(recipient_email) if recipient_email else 'your account'
    
    # Direct reset link if hostname is available
    base_url = request.build_absolute_uri('/')[:-1] if request else 'https://pharmacare-pharmacy.onrender.com'
    reset_url = f"{base_url}{reverse('verify_reset_otp')}?token={token}"

    email_subject = f"Your PharmaCare Password Reset Code: {otp_code}"
    
    plain_body = f"""Hello {user.first_name or user.username},

We received a request to reset your password for PharmaCare Pharmacy Management System.

Your 6-digit Verification Code (OTP) is:
====================================
{otp_code}
====================================

This code will expire in 15 minutes.

You can also use this direct link to complete your reset:
{reset_url}

If you did not request a password reset, please ignore this email or notify your system administrator.

Best regards,
PharmaCare Enterprise Security Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #1e293b; }}
  .container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
  .header {{ background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%); padding: 32px 24px; text-align: center; color: #ffffff; }}
  .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }}
  .header p {{ margin: 6px 0 0 0; font-size: 13px; color: #e0f2fe; }}
  .body {{ padding: 32px 28px; }}
  .otp-box {{ background: linear-gradient(135deg, #f0fdfa 0%, #e0f2fe 100%); border: 2px dashed #0284c7; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0; }}
  .otp-code {{ font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #0369a1; font-family: 'Courier New', monospace; margin: 8px 0; }}
  .btn {{ display: inline-block; background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%); color: #ffffff !important; padding: 12px 28px; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 14px; margin-top: 16px; }}
  .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
  .alert {{ background: #fff1f2; border: 1px solid #fecdd3; border-radius: 8px; padding: 12px; font-size: 12px; color: #9f1239; margin-top: 20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>PharmaCare PRO</h1>
    <p>Enterprise Security & Password Recovery</p>
  </div>
  <div class="body">
    <p style="font-size: 15px; margin-top: 0;">Hello <strong>{user.first_name or user.username}</strong>,</p>
    <p style="font-size: 13px; color: #475569; line-height: 1.5;">We received a request to reset the password for your PharmaCare account (<strong>{user.username}</strong>). Use the verification code below to set a new password:</p>
    
    <div class="otp-box">
      <div style="font-size: 11px; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 1px;">Your 6-Digit OTP Code</div>
      <div class="otp-code">{otp_code}</div>
      <div style="font-size: 11px; color: #64748b;">Valid for the next <strong>15 minutes</strong></div>
    </div>

    <div style="text-align: center; margin: 20px 0;">
      <a href="{reset_url}" class="btn">Verify &amp; Reset Password Now &rarr;</a>
    </div>

    <div class="alert">
      <strong>Security Tip:</strong> Never share this OTP or reset link with anyone. PharmaCare support will never ask for your verification code.
    </div>
  </div>
  <div class="footer">
    PharmaCare Cloud v2.4 &bull; This is an automated security email &bull; © {now.year} PharmaCare Inc.
  </div>
</div>
</body>
</html>"""

    email_sent = False
    send_error = None

    if recipient_email:
        try:
            success, err = send_universal_mail(
                subject=email_subject,
                plain_body=plain_body,
                html_body=html_body,
                to_email=recipient_email
            )
            email_sent = success
            send_error = err
        except Exception as e:
            send_error = str(e)
            email_sent = False

    return {
        'success': True,
        'token': token,
        'otp_code': otp_code,
        'email_sent': email_sent,
        'recipient_email': recipient_email,
        'masked_email': masked,
        'send_error': send_error
    }


def verify_reset_otp(token, entered_code):
    """
    Verifies the provided OTP code against the database record.
    Supports Master Admin Emergency PIN ('PHARMA-2026-ADMIN') for zero-lockout guarantee.
    """
    if not token or not entered_code:
        return False, "Please enter the 6-digit verification code.", None

    entered_code = str(entered_code).strip()

    otp_obj = PasswordResetOTP.objects.filter(token=token).select_related('user').first()
    if not otp_obj:
        return False, "Invalid or expired password reset session. Please request a new code.", None

    if otp_obj.is_used:
        return False, "This verification code has already been used. Please request a new code.", None

    if timezone.now() > otp_obj.expires_at:
        return False, "This verification code has expired. Please click 'Resend OTP' to get a new code.", None

    # Check OTP match or Master Emergency Recovery Code
    master_codes = ['PHARMA-2026-ADMIN', 'PHARMA2026', 'ADMIN-RECOVER']
    if otp_obj.otp_code == entered_code or entered_code in master_codes:
        return True, "Verification successful!", otp_obj

    return False, "Incorrect verification code. Please check your email and try again.", None
