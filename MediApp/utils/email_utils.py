import json
import os
import ssl
import urllib.request
import urllib.error
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.conf import settings


def send_via_resend(to_email, subject, html_content, text_content=None, from_email=None):
    """
    Dispatches email via Resend HTTPS REST API (Port 443).
    100% reliable on Cloud hosting platforms like Render where SMTP ports are blocked.
    """
    api_key = getattr(settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
    if not api_key:
        return False, "No RESEND_API_KEY configured"

    from_addr = from_email or getattr(settings, 'RESEND_FROM_EMAIL', '') or os.environ.get('RESEND_FROM_EMAIL', 'PharmaCare <onboarding@resend.dev>')
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "User-Agent": "PharmaCare-App/1.0"
    }
    
    recipients = [to_email] if isinstance(to_email, str) else list(to_email)
    recipients = [r.strip() for r in recipients if r and r.strip()]
    if not recipients:
        return False, "No recipient email address provided"

    payload = {
        "from": from_addr,
        "to": recipients,
        "subject": subject,
        "html": html_content,
    }
    if text_content:
        payload["text"] = text_content

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode('utf-8')
            return True, None
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode('utf-8')
        try:
            err_json = json.loads(err_msg)
            err_msg = err_json.get('message', err_msg)
        except Exception:
            pass
        return False, f"Resend API Error: {err_msg}"
    except Exception as exc:
        return False, f"Resend Error: {exc}"


def send_universal_mail(subject, plain_body, html_body, to_email, from_email=None, conn=None):
    """
    Smart unified email dispatcher:
    1. If RESEND_API_KEY is configured (Render Cloud), uses HTTPS port 443 (100% unblocked).
    2. Falls back seamlessly to Django SMTP backend (for local dev or custom SMTP).
    """
    resend_key = getattr(settings, 'RESEND_API_KEY', '') or os.environ.get('RESEND_API_KEY', '')
    if resend_key:
        success, err = send_via_resend(to_email, subject, html_body, text_content=plain_body, from_email=from_email)
        if success:
            return True, None
        # If Resend failed and SMTP credentials exist, attempt SMTP fallback
        if not getattr(settings, 'EMAIL_HOST_PASSWORD', ''):
            return False, err

    # Fallback to standard SMTP
    try:
        if conn is None:
            conn = get_email_connection()
        send_mail(
            subject=subject,
            message=plain_body,
            html_message=html_body,
            from_email=from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', ''),
            recipient_list=[to_email] if isinstance(to_email, str) else list(to_email),
            fail_silently=False,
            connection=conn
        )
        return True, None
    except Exception as exc:
        return False, str(exc)


def get_email_connection():
    """Create SMTP connection with SSL certificate verification fallback for Windows and Cloud environments."""
    ssl_context = None
    try:
        ssl_context = ssl._create_unverified_context()
    except Exception:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        except Exception:
            pass

    use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
    use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
    if use_ssl and use_tls:
        use_tls = False

    return get_connection(
        backend=getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'),
        host=getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com'),
        port=getattr(settings, 'EMAIL_PORT', 465 if use_ssl else 587),
        username=getattr(settings, 'EMAIL_HOST_USER', ''),
        password=getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout=getattr(settings, 'EMAIL_TIMEOUT', 10),
        ssl_context=ssl_context,
    )


def send_reminder_email(customer, reminder):
    """Send email notification to the customer for a medicine reminder.

    Returns:
        dict: {'success': bool, 'error': str or None}
    """
    if not customer:
        return {'success': False, 'error': 'No customer provided.'}

    if not customer.email or not customer.email.strip():
        return {'success': False, 'error': f"Customer '{customer.name}' has no email address configured."}

    medicine_name = reminder.medicine.name if (reminder and reminder.medicine) else "Your Scheduled Medicine"
    reminder_text = reminder.reminder_text if reminder else "Please check your medicine dosage and schedule."
    period_display = reminder.get_period_display() if reminder else "Scheduled"

    next_send_str = "N/A"
    if reminder and reminder.next_send:
        next_send_str = reminder.next_send.strftime("%B %d, %Y at %I:%M %p")
    elif reminder and reminder.send_at:
        next_send_str = reminder.send_at.strftime("%B %d, %Y at %I:%M %p")

    subject = f"⏰ Medicine Reminder: {medicine_name} - PharmaCare"

    plain_message = (
        f"Dear {customer.name},\n\n"
        f"This is a gentle reminder from PharmaCare regarding your medicine schedule.\n\n"
        f"Medicine: {medicine_name}\n"
        f"Schedule: {period_display}\n"
        f"Details: {reminder_text}\n"
        f"Next Scheduled Reminder: {next_send_str}\n\n"
        f"Please ensure you take your prescription as directed or refill your supply on time.\n\n"
        f"Warm regards,\n"
        f"PharmaCare Care Team"
    )

    html_message = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Roboto, Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 580px; margin: 30px auto; background: #ffffff; border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08); overflow: hidden; border: 1px solid #e5e7eb; }}
    .header {{ background: linear-gradient(135deg, #0284c7, #0369a1); padding: 30px 36px; text-align: center; }}
    .header h1 {{ color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 0.5px; }}
    .header p  {{ color: #e0f2fe; margin: 6px 0 0; font-size: 14px; }}
    .badge {{ display: inline-block; background: #f59e0b; color: #fff; border-radius: 20px;
              padding: 4px 14px; font-size: 12px; font-weight: 700; margin-top: 12px; }}
    .body {{ padding: 32px 36px; }}
    .body p {{ color: #374151; font-size: 15px; line-height: 1.6; margin: 0 0 16px; }}
    .card {{ background: #f0f9ff; border-left: 4px solid #0284c7; border-radius: 8px;
             padding: 20px; margin: 20px 0; }}
    .card h2 {{ margin: 0 0 12px; color: #0369a1; font-size: 18px; }}
    .card table {{ width: 100%; border-collapse: collapse; font-size: 14px; color: #4b5563; }}
    .card td {{ padding: 6px 0; }}
    .card td:first-child {{ font-weight: 600; width: 130px; color: #1f2937; }}
    .pill {{ display: inline-block; background: #e0f2fe; color: #0369a1; border-radius: 12px;
             padding: 2px 10px; font-weight: 600; font-size: 13px; }}
    .footer {{ background: #f8fafc; text-align: center; padding: 18px 36px; font-size: 12px; color: #9ca3af; border-top: 1px solid #f1f5f9; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>💊 PharmaCare</h1>
      <p>Your Health & Wellness Partner</p>
      <span class="badge">⏰ Medicine Reminder</span>
    </div>
    <div class="body">
      <p>Dear <strong>{customer.name}</strong>,</p>
      <p>This is a friendly reminder regarding your medicine prescription and refill schedule:</p>

      <div class="card">
        <h2>💊 {medicine_name}</h2>
        <table>
          <tr>
            <td>Reminder Note</td>
            <td><strong>{reminder_text}</strong></td>
          </tr>
          <tr>
            <td>Frequency</td>
            <td><span class="pill">{period_display}</span></td>
          </tr>
          <tr>
            <td>Next Schedule</td>
            <td>{next_send_str}</td>
          </tr>
        </table>
      </div>

      <p>Please ensure to follow your prescription guidelines. If you need a refill, visit or contact PharmaCare!</p>
    </div>
    <div class="footer">
      © PharmaCare Pharmacy Management System<br>
      You are receiving this automated email based on your pharmacy medication schedule.
    </div>
  </div>
</body>
</html>
"""

    success, err = send_universal_mail(
        subject=subject,
        plain_body=plain_message,
        html_body=html_message,
        to_email=customer.email.strip(),
    )
    return {'success': success, 'error': err}


def send_stock_available_email(medicine, customers):
    """
    Send a stock-availability notification email to a list of permanent customers.

    Args:
        medicine: A Medicine model instance that is now in stock.
        customers: Queryset or list of Customer instances with valid emails.

    Returns:
        dict with keys 'sent' (int) and 'errors' (list of str).
    """
    sent = 0
    errors = []

    subject = f"✅ {medicine.name} is Now Available at PharmaCare!"

    for customer in customers:
        if not customer.email:
            errors.append(f"Customer {customer.name} has no email address.")
            continue

        plain_message = (
            f"Dear {customer.name},\n\n"
            f"Great news! '{medicine.name}' is now back in stock at our pharmacy.\n\n"
            f"Medicine Details:\n"
            f"  - Name    : {medicine.name}\n"
            f"  - Category: {medicine.category.name if medicine.category else 'N/A'}\n"
            f"  - Price   : ₹{medicine.price}\n"
            f"  - Stock   : {medicine.total_quantity} units available\n\n"
            f"Hurry in before it runs out!\n\n"
            f"Warm regards,\nPharmaCare Team"
        )

        html_message = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 580px; margin: 30px auto; background: #ffffff; border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #1a73e8, #0d47a1); padding: 30px 36px; text-align: center; }}
    .header h1 {{ color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 0.5px; }}
    .header p  {{ color: #bbdefb; margin: 6px 0 0; font-size: 14px; }}
    .badge {{ display: inline-block; background: #43a047; color: #fff; border-radius: 20px;
              padding: 4px 14px; font-size: 12px; font-weight: 700; margin-top: 12px; }}
    .body {{ padding: 32px 36px; }}
    .body p {{ color: #333; font-size: 15px; line-height: 1.7; margin: 0 0 16px; }}
    .medicine-card {{ background: #f0f7ff; border-left: 4px solid #1a73e8; border-radius: 8px;
                      padding: 18px 22px; margin: 20px 0; }}
    .medicine-card h2 {{ margin: 0 0 12px; color: #1a73e8; font-size: 18px; }}
    .medicine-card table {{ width: 100%; border-collapse: collapse; font-size: 14px; color: #444; }}
    .medicine-card td {{ padding: 6px 0; }}
    .medicine-card td:first-child {{ font-weight: 600; width: 110px; color: #222; }}
    .stock-pill {{ display: inline-block; background: #e8f5e9; color: #2e7d32; border-radius: 12px;
                   padding: 2px 10px; font-weight: 700; font-size: 13px; }}
    .cta {{ text-align: center; margin: 28px 0 8px; }}
    .cta a {{ background: linear-gradient(135deg, #1a73e8, #0d47a1); color: #fff; text-decoration: none;
               padding: 13px 32px; border-radius: 8px; font-size: 15px; font-weight: 600;
               display: inline-block; letter-spacing: 0.3px; }}
    .footer {{ background: #f4f6f9; text-align: center; padding: 16px 36px; font-size: 12px; color: #888; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <h1>💊 PharmaCare</h1>
      <p>Your trusted neighborhood pharmacy</p>
      <span class="badge">✅ Back in Stock!</span>
    </div>
    <div class="body">
      <p>Dear <strong>{customer.name}</strong>,</p>
      <p>We're excited to let you know that a medicine you may need is now <strong>back in stock</strong> and ready for pickup!</p>

      <div class="medicine-card">
        <h2>💊 {medicine.name}</h2>
        <table>
          <tr>
            <td>Category</td>
            <td>{medicine.category.name if medicine.category else 'N/A'}</td>
          </tr>
          <tr>
            <td>Price</td>
            <td><strong>₹{medicine.price}</strong></td>
          </tr>
          <tr>
            <td>Available</td>
            <td><span class="stock-pill">{medicine.total_quantity} units</span></td>
          </tr>
        </table>
      </div>

      <p>Don't wait — stock is limited! Visit us or call us to reserve your supply.</p>

      <div class="cta">
        <a href="#">Visit PharmaCare Today →</a>
      </div>
    </div>
    <div class="footer">
      © PharmaCare | You're receiving this because you're a valued permanent member.<br>
      To unsubscribe, please contact us directly.
    </div>
  </div>
</body>
</html>
"""

        success, err = send_universal_mail(
            subject=subject,
            plain_body=plain_message,
            html_body=html_message,
            to_email=customer.email.strip(),
        )
        if success:
            sent += 1
        else:
            errors.append(f"Failed to email {customer.name} ({customer.email}): {err}")

    return {"sent": sent, "errors": errors}
