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
    validate it server-side, then send an email to
    the owner using SMTP credentials from the .env file.

    Returns JSON:
        { "success": true }                          on success
        { "success": false, "error": "..." }         on failure
    """
    data = request.get_json(silent=True) or {}

    # ── Server-side validation ─────────────────────────────
    errors = {}
    first_name = data.get("firstName", "").strip()
    last_name  = data.get("lastName",  "").strip()
    email      = data.get("email",     "").strip()
    phone      = data.get("phone",     "").strip()
    message    = data.get("message",   "").strip()

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
        return jsonify({"success": False, "errors": errors}), 400

    # ── Build the email ────────────────────────────────────
    owner_email  = os.getenv("OWNER_EMAIL")        # Josiah's email address
    smtp_user    = os.getenv("SMTP_USER")          # Sending Gmail / SMTP account
    smtp_pass    = os.getenv("SMTP_PASSWORD")      # App password for that account
    smtp_host    = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port    = int(os.getenv("SMTP_PORT", "465"))

    if not all([owner_email, smtp_user, smtp_pass]):
        app.logger.error("Email credentials not configured in .env")
        return jsonify({
            "success": False,
            "error": "Server email is not configured yet. Please contact Josiah directly."
        }), 500

    subject = f"New Booking Inquiry from {first_name} {last_name}"

    # Plain-text body
    body_text = f"""
New booking inquiry from the Josiah Guenther website
=====================================================

Name:    {first_name} {last_name}
Email:   {email}
Phone:   {phone}

Message:
{message}

=====================================================
This message was sent via the contact form at josiah-guenther.com
"""

    # HTML body (nicely formatted for email clients that support it)
    body_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Georgia, serif; background: #f4f4f4; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 560px; margin: 40px auto; background: #fff; border-radius: 4px;
                overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
    .header {{ background: #0e1117; padding: 28px 32px; }}
    .header h1 {{ color: #4a90c8; font-size: 1.1rem; letter-spacing: 0.12em;
                  text-transform: uppercase; margin: 0; }}
    .body {{ padding: 32px; }}
    .field {{ margin-bottom: 20px; }}
    .label {{ font-size: 0.75rem; font-weight: bold; color: #888;
              text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px; }}
    .value {{ font-size: 1rem; color: #222; }}
    .message-box {{ background: #f9f9f9; border-left: 3px solid #4a90c8;
                    padding: 16px; border-radius: 2px; white-space: pre-wrap; }}
    .footer {{ background: #f4f4f4; padding: 16px 32px; font-size: 0.78rem;
               color: #aaa; text-align: center; }}
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
        <div class="value"><a href="mailto:{email}">{email}</a></div>
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
      Sent via the contact form at josiah-guenther.com
    </div>
  </div>
</body>
</html>
"""

    # ── Send via SMTP ──────────────────────────────────────
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = smtp_user
        msg["To"]      = owner_email
        msg["Reply-To"] = email   # Reply goes directly to the inquirer

        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        context = ssl.create_default_context()

        # Port 465 → SSL from the start; port 587 → STARTTLS
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, owner_email, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, owner_email, msg.as_string())

        app.logger.info(f"Contact email sent from {email}")
        return jsonify({"success": True})

    except smtplib.SMTPAuthenticationError:
        app.logger.error("SMTP authentication failed — check SMTP_USER and SMTP_PASSWORD in .env")
        return jsonify({
            "success": False,
            "error": "Email authentication failed. Please try again later."
        }), 500

    except Exception as exc:
        app.logger.error(f"Email send error: {exc}")
        return jsonify({
            "success": False,
            "error": "Something went wrong sending your message. Please try again."
        }), 500


# ═══════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    # debug=True gives you live reload while developing.
    # Set debug=False (or remove) before deploying to production.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
