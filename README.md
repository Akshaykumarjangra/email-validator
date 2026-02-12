# 🚀 High-Volume Email Verifier

A professional, high-performance Python tool for batch email verification. Handles up to 100k+ emails using async concurrency, SQLite caching, and a tiered validation system.

## 🛠 Features
- **Tiered Validation:**
  - **Level 1 (Regex):** Instant syntax check.
  - **Level 2 (Local RAG):** Knowledge base of disposable/spam domains.
  - **Level 3 (DNS MX):** Real-time mail server discovery.
  - **Level 4 (SMTP Handshake):** Deep `RCPT TO` check for mailbox existence.
- **Performance:** Async FIFO queue with configurable worker count.
- **Persistence:** Full SQLite caching to prevent redundant lookups.
- **Reporting:** Real-time terminal dashboard and CSV export.

## 📋 Requirements
- Python 3.8+
- Requirements: `rich`, `aiosmtplib`, `dnspython`, `email-validator`

## 🚀 Getting Started
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run verification:**
   ```bash
   python main.py emails.csv
   ```

## ⚠️ VPS Usage (Recommended)
Local ISPs often block port 25. For 100% accurate SMTP results, run this tool on a VPS (AWS, DigitalOcean, etc.) with port 25 enabled.

---
Built with ❤️ for High-Volume Data Processing.
