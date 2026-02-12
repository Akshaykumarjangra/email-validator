import re
import asyncio
import dns.resolver
import aiosmtplib
import requests
import os
from email_validator import validate_email, EmailNotValidError

class EmailValidator:
    def __init__(self, db):
        self.db = db
        # Basic regex for fallback
        self.regex = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
        self.worker_url = os.getenv("VPS_WORKER_URL") # e.g., http://vps-ip:8000/verify
        self.worker_token = os.getenv("VPS_WORKER_TOKEN")

    async def validate(self, email):
        email = email.lower().strip()
        
        # 1. Regex/Syntax Check
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            return "Invalid", str(e)

        domain = email.split('@')[1]

        # 2. Local RAG / Knowledge Base Check
        domain_info = self.db.get_domain_info(domain)
        if isinstance(domain_info, str): # category from domain_knowledge
            return "Risky", f"Domain flagged as {domain_info}"

        # 3. DNS Check (MX records)
        mx_records = []
        if isinstance(domain_info, tuple): # cached from domain_cache
            mx_records = [domain_info[1]] if domain_info[0] else []
        else:
            try:
                answers = await asyncio.to_thread(dns.resolver.resolve, domain, 'MX')
                mx_records = sorted([str(r.exchange).strip('.') for r in answers], key=lambda x: x)
                self.db.save_domain_cache(domain, True, mx_records[0])
            except Exception:
                self.db.save_domain_cache(domain, False, "")
                return "Invalid", "No MX records found"

        if not mx_records:
            return "Invalid", "No MX records"

        # 4. SMTP Handshake (Deep Check)
        # HYBRID STRATEGY: 
        # If we are on Vercel (Port 25 blocked), we call the VPS worker.
        # Otherwise, we perform local SMTP.
        if self.worker_url:
            return await self._check_smtp_via_worker(email, mx_records[0])
        else:
            return await self._check_smtp_local(email, mx_records[0])

    async def _check_smtp_via_worker(self, email, mx_host):
        try:
            # We use long-polling or a simple POST to our VPS worker
            # In a real setup, this would be an async request
            response = await asyncio.to_thread(
                requests.post, 
                self.worker_url, 
                json={"email": email, "mx": mx_host, "token": self.worker_token},
                timeout=15
            )
            if response.ok:
                data = response.json()
                return data['status'], data['details']
            return "Unknown", f"Worker Error: {response.text}"
        except Exception as e:
            # Fallback to DNS-only if worker is down
            return "Valid", f"DNS Passed (SMTP Worker unreachable: {str(e)})"

    async def _check_smtp_local(self, email, mx_host):
        try:
            async with aiosmtplib.SMTP(hostname=mx_host, port=25, timeout=10) as smtp:
                await smtp.ehlo()
                code, message = await smtp.mail("verify@example.com")
                if code != 250:
                    return "Unknown", f"SMTP Mail From failed: {message}"

                code, message = await smtp.rcpt(email)
                if code == 250:
                    return "Valid", "SMTP Verified"
                elif code == 550:
                    return "Invalid", "User does not exist (550)"
                else:
                    return "Risky", f"SMTP Response: {code} {message}"
        except Exception as e:
            # On Vercel, this WILL fail.
            if "WinError 10013" in str(e) or "denied" in str(e).lower():
                return "Valid", "DNS Verified (Deep SMTP blocked locally)"
            return "Error", f"SMTP Connect failed: {str(e)}"
