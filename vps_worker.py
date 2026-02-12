import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aiosmtplib

app = FastAPI()

class VerifyRequest(BaseModel):
    email: str
    mx: str
    token: str

import os
from dotenv import load_dotenv
load_dotenv()

# Security Token (Must match .env on Vercel)
SECURE_TOKEN = os.getenv("VPS_WORKER_TOKEN", "ROCKET-VERIFY-SECURE-2026")

@app.post("/verify")
async def verify_smtp(req: VerifyRequest):
    if req.token != SECURE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid Security Token")

    try:
        async with aiosmtplib.SMTP(hostname=req.mx, port=25, timeout=10) as smtp:
            await smtp.ehlo()
            code, message = await smtp.mail("vps-verify@rocketverify.com")
            if code != 250:
                return {"status": "Unknown", "details": f"SMTP Mail From failed: {message}"}

            code, message = await smtp.rcpt(req.email)
            if code == 250:
                return {"status": "Valid", "details": "SMTP Handshake Verified (VPS)"}
            elif code == 550:
                return {"status": "Invalid", "details": "User does not exist (550)"}
            else:
                return {"status": "Risky", "details": f"SMTP Response: {code} {message}"}
    except Exception as e:
        return {"status": "Error", "details": str(e)}

if __name__ == "__main__":
    print(f"RocketVerify VPS Worker starting... Ensuring Port 25 is open.")
    uvicorn.run(app, host="0.0.0.0", port=8000)
