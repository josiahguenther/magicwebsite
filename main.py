import resend
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# ── Load environment variables from .env ──────────────────
load_dotenv()

# ── Create the Flask app ──────────────────────────────────
app = Flask(__name__)

# Secret key used by Flask for session security (not exposed to front-end)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

resend.api_key = os.getenv("RESEND_API_KEY")

# ═══════════════════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════════════════

@app.route("/")
def home():
    """Render the Home page."""
    return render_template("home.html")


@app.route("/services")
def services():
    """Render the Services page."""
    return render_template("services.html")


@app.route("/contact")
def contact():
    """Render the Contact page."""
    return render_template("contact.html")


# ═══════════════════════════════════════════════════════════
#  CONTACT FORM  –  POST /send-email
# ═══════════════════════════════════════════════════════════

@app.route("/send-email", methods=["POST"])
def send_email():
    """
    Receive the contact form submission as JSON,
    validate it server-side, then send an email
    through the Resend API.
    """
    data = request.get_json(silent=True) or {}

    # ── Server-side validation ─────────────────────────────
    errors = {}

    first_name = data.get("firstName", "").strip()
    last_name = data.get("lastName", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    message = data.get("message", "").strip()

    if not first_name:
        errors["firstName"] = "First name is required."

    if not last_name:
        errors["lastName"] = "Last name is required."

    if not email or "@" not in email:
        errors["email"] = "A valid email address is required."

    if not phone or len(phone) < 7:
        errors["phone"] = "A valid phone number is required."

    if not message or len(message) < 10:
        errors["message"] = "Please include a message of at least 10 characters."

    if errors:
        return jsonify({
            "success": False,
            "errors": errors
        }), 400

    owner_email = os.getenv("OWNER_EMAIL")

    if not owner_email:
        app.logger.error("OWNER_EMAIL environment variable is missing.")
        return jsonify({
            "success": False,
            "error": "Server email is not configured."
        }), 500

    subject = f"New Booking Inquiry from {first_name} {last_name}"

    body_text = f"""
New booking inquiry from the Josiah Guenther website
=====================================================

Name:    {first_name} {last_name}
Email:   {email}
Phone:   {phone}

Message:
{message}

=====================================================
This message was sent via the contact form at josiahguenthermagic.com
"""

    body_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    font-family: Georgia, serif;
    background: #f4f4f4;
    margin: 0;
    padding: 0;
}}

.wrapper {{
    max-width: 560px;
    margin: 40px auto;
    background: white;
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,.08);
}}

.header {{
    background: #0e1117;
    padding: 28px 32px;
}}

.header h1 {{
    color: #4a90c8;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: .1em;
}}

.body {{
    padding: 32px;
}}

.field {{
    margin-bottom: 20px;
}}

.label {{
    font-size: .75rem;
    font-weight: bold;
    color: #888;
    text-transform: uppercase;
}}

.value {{
    font-size: 1rem;
    color: #222;
}}

.message-box {{
    background: #f9f9f9;
    border-left: 3px solid #4a90c8;
    padding: 16px;
    white-space: pre-wrap;
}}

.footer {{
    background: #f4f4f4;
    padding: 16px;
    text-align: center;
    color: #999;
    font-size: .8rem;
}}
</style>
</head>

<body>

<div class="wrapper">

<div class="header">
<h1>New Booking Inquiry</h1>
</div>

<div class="body">

<div class="field">
<div class="label">Name</div>
<div class="value">{first_name} {last_name}</div>
</div>

<div class="field">
<div class="label">Email</div>
<div class="value">{email}</div>
</div>

<div class="field">
<div class="label">Phone</div>
<div class="value">{phone}</div>
</div>

<div class="field">
<div class="label">Message</div>
<div class="message-box">{message}</div>
</div>

</div>

<div class="footer">
Sent via josiahguenthermagic.com
</div>

</div>

</body>
</html>
"""

    try:
        resend.Emails.send({
            "from": "Josiah Guenther Magic <josiah@josiahguenthermagic.com>",
            "to": [owner_email],
            "subject": subject,
            "text": body_text,
            "html": body_html,
            "reply_to": email
        })

        app.logger.info(f"Contact email sent from {email}")

        return jsonify({
            "success": True
        })

    except Exception as exc:
        app.logger.exception(exc)

        return jsonify({
            "success": False,
            "error": "Something went wrong sending your message."
        }), 500


# ═══════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # debug=True gives you live reload while developing.
    # Set debug=False (or remove) before deploying to production.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
