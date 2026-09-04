import resend
import os
import smtplib
import ssl
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from dotenv import load_dotenv

def get_db_connection():
    conn = sqlite3.connect("useless_accomplishments.db")
    conn.row_factory = sqlite3.Row
    return conn

# ── Load environment variables from .env ──────────────────
load_dotenv()

# ── Create the Flask app ──────────────────────────────────
app = Flask(__name__)

# Secret key used by Flask for session security (not exposed to front-end)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

resend.api_key = os.getenv("RESEND_API_KEY")

def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS accomplishments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()

# ═══════════════════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════════════════

@app.route("/")
def home():
    """Render the Home page."""
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/services")
def services():
    """Render the Services page."""
    return render_template("services.html")


@app.route("/contact")
def contact():
    """Render the Contact page."""
    return render_template("contact.html")


@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")

@app.route("/do-not-click", methods=["GET", "POST"])
def do_not_click():

    if request.method == "POST":
        name = request.form.get("name")

        if name and name.strip():
            conn = get_db_connection()

            conn.execute(
                "INSERT INTO accomplishments (name) VALUES (?)",
                (name.strip(),)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("wall_of_useless_accomplishments"))

    return render_template("do_not_click.html")


@app.route("/wall-of-useless-accomplishments")
def wall_of_useless_accomplishments():

    conn = get_db_connection()

    names = conn.execute(
        "SELECT name FROM accomplishments ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "wall_of_useless_accomplishments.html",
        names=names
    )
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

       # ──────────────────────────────────────────────────────
        # Send confirmation email to the customer
        # (If this fails, don't lose the booking inquiry.)
        # ──────────────────────────────────────────────────────
        try:
            confirmation_subject = "Thanks for contacting Josiah Guenther Magic!"
    
            confirmation_text = f"""
    Hi {first_name},
    
    Thank you for contacting Josiah Guenther Magic!
    
    I've received your inquiry and will personally review it as soon as possible.
    
    I do my best to respond within 1–2 business days.
    
    
    Have a magical day!
    
    Josiah Guenther
    """
    
            confirmation_html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Georgia, serif; background:#f4f4f4; padding:40px;">
    <div style="max-width:600px; margin:auto; background:white; padding:40px; border-radius:6px;">
    
    <h2 style="color:#4a90c8;">
    Thanks for reaching out!
    </h2>
    
    <p>Hi {first_name},</p>
    
    <p>
    Thank you for contacting <strong>Josiah Guenther Magic</strong>.
    I've received your inquiry and will personally review it as soon as possible.
    </p>
    
    <p>
    I do my best to respond within <strong>1–2 business days</strong>.
    </p>
    
    
    <hr>
    
    <p><strong>Your message:</strong></p>
    
    <div style="
    background:#f8f8f8;
    padding:16px;
    border-left:3px solid #4a90c8;
    white-space:pre-wrap;
    ">
    {message}
    </div>
    
    <p style="margin-top:30px;">
    Have a magical day!
    </p>
    
    <p>
    <strong>Josiah Guenther</strong><br>
    Your (Future) Guide to Wonderland
    </p>
    
    </div>
    </body>
    </html>
    """
    
            resend.Emails.send({
                "from": "Josiah Guenther Magic <josiah@josiahguenthermagic.com>",
                "to": [email],
                "subject": confirmation_subject,
                "text": confirmation_text,
                "html": confirmation_html
            })
    
            app.logger.info(f"Confirmation email sent to {email}")

        except Exception as confirmation_error:
            app.logger.warning(
                f"Could not send confirmation email to {email}: {confirmation_error}"
            )
    
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
