import os
import asyncio
import io
import csv
import re
from flask import Flask, request, jsonify, render_template, send_file, session
from flask_cors import CORS
from database import Database
from validator import EmailValidator
from auth import auth_bp, login_manager, setup_oauth
from flask_login import current_user, login_required
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key")
CORS(app)

# Initialize Login Manager
login_manager.init_app(app)
app.register_blueprint(auth_bp)

db = Database("saas_results.db")
validator = EmailValidator(db)

# Mock RAG setup
db.add_domain_knowledge(["mailinator.com", "temp-mail.org"], "disposable")

@app.route('/')
def index():
    return render_template('index.html', user=current_user)

@app.route('/api/verify', methods=['POST'])
@login_required
async def verify_emails():
    # 1. Access Control & Limits
    if current_user.role != 'admin':
        if current_user.credits_used >= current_user.credits_total:
            return jsonify({"error": "Trial limit reached (4,000 emails). Please upgrade."}), 403

    data = request.json
    emails_text = data.get('emails', '')
    emails = re.split(r'[,\n\s]+', emails_text.strip())
    emails = [e.strip() for e in emails if e.strip()]
    
    if not emails:
        return jsonify({"error": "No emails provided"}), 400

    # 2. Batch Cap Check (1k emails at once)
    if current_user.role != 'admin' and len(emails) > int(os.getenv("BATCH_CAP", 1000)):
        return jsonify({"error": f"Batch limit exceeded. Max {os.getenv('BATCH_CAP')} emails per request."}), 400

    # 3. Processing
    results = []
    async def process_email(email):
        # In a real hybrid setup, this would call the VPS worker for SMTP
        status, details = await validator.validate(email)
        db.log_verification(current_user.id, email, status, details)
        return {"email": email, "status": status, "details": details}

    # Gather results concurrently
    processed_count = len(emails)
    results = await asyncio.gather(*(process_email(e) for e in emails))
    
    # Update credits
    if current_user.role != 'admin':
        db.update_user_credits(current_user.id, processed_count)
    
    return jsonify(results)

@app.route('/api/stats')
@login_required
def get_stats():
    logs = db.get_user_logs(current_user.id, limit=50)
    return jsonify({
        "credits_used": current_user.credits_used,
        "credits_total": current_user.credits_total,
        "logs": [{"email": l[0], "status": l[1], "details": l[2], "time": l[3]} for l in logs]
    })

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        return "Access Denied", 403
    logs = db.get_all_logs(limit=200)
    return render_template('admin.html', logs=logs)

@app.route('/api/export', methods=['POST'])
@login_required
def export_results():
    data = request.json
    results = data.get('results', [])
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "Status", "Comment/Details"])
    for res in results:
        writer.writerow([res.get('email'), res.get('status'), res.get('details')])
    
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name='verification_results.csv'
    )

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("PORT", 5000))
    app.run(debug=debug_mode, port=port)
else:
    # This branch runs when imported by a production WSGI/ASGI server
    # We ensure debug is definitely off
    app.debug = False
