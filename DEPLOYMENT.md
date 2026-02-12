# 🚀 RocketVerify SaaS Deployment Guide

Your Email Verification tool is now a professional SaaS! Follow these steps to go live globally.

## 1. Prepare Ground Control (Vercel)
The UI and API will run and scale on Vercel.
1.  **Push your code** to a GitHub repository.
2.  **Connect to Vercel:** Create a new project from your repo.
3.  **Environment Variables:** Add all variables from `.env` to Vercel:
    - `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ADMIN_EMAIL`.
    - **Database:** Connect a Supabase PostgreSQL DB and put the URL in `DATABASE_URL`.

## 2. Launch the Deep Check Node (VPS)
Since Vercel blocks Port 25, run the logic node on a VPS.
1.  **Get a VPS:** DigitalOcean, Hetzner, or AWS (ensure Port 25 is open).
2.  **Run the worker:**
    ```bash
    pip install fastapi uvicorn aiosmtplib pydantic
    python vps_worker.py
    ```
3.  **Connect to Vercel:** Add `VPS_WORKER_URL` (your-vps-ip:8000/verify) and `VPS_WORKER_TOKEN` to Vercel Env Vars.

## 3. SaaS Business Logic
- **Admin:** Login with `akg45272@gmail.com` for unlimited access and Global Logs via `/admin`.
- **Trial Users:** Limited to 4,000 emails total across all sessions.
- **Batching:** Strictly capped at 1,000 emails per request for performance.
- **Payments:** Stripe integration points are ready in `app.py`.

---
**Verified Professional Deployment Strategy.**
