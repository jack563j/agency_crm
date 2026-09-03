"""
Agency CRM — New Customer Setup Script
=======================================
Run this script ONCE for every new customer you onboard.
It generates a complete set of environment variables you paste into Render.

Usage (Windows PowerShell):
    python customer_setup/new_customer.py

Usage (Mac / Linux):
    python3 customer_setup/new_customer.py
"""

import secrets
import string
import datetime

# ─────────────────────────────────────────────
# FILL THESE IN FOR EACH NEW CUSTOMER
# ─────────────────────────────────────────────
CUSTOMER_NAME     = input("Customer / Business name: ").strip()
CUSTOMER_EMAIL    = input("Customer's email address: ").strip()
NEON_DATABASE_URL = input("Paste the Neon DATABASE_URL for this customer: ").strip()
RENDER_DOMAIN     = input("Paste the Render app URL (e.g. acme-crm.onrender.com): ").strip().replace("https://", "").replace("http://", "").strip("/")
GEMINI_API_KEY    = input("Paste the Gemini API key (yours or theirs): ").strip()

# ─────────────────────────────────────────────
# AUTO-GENERATED — DO NOT EDIT BELOW
# ─────────────────────────────────────────────
alphabet   = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
SECRET_KEY = "".join(secrets.choice(alphabet) for _ in range(50))

slug = CUSTOMER_NAME.lower().replace(" ", "_").replace("-", "_")
ADMIN_USERNAME = f"admin_{slug}"
ADMIN_PASSWORD = secrets.token_urlsafe(12)

timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

output = f"""
╔══════════════════════════════════════════════════════════════════════╗
║           AGENCY CRM — CUSTOMER DEPLOYMENT PACKAGE                  ║
║  Customer : {CUSTOMER_NAME:<54} ║
║  Generated: {timestamp:<54} ║
╚══════════════════════════════════════════════════════════════════════╝

STEP 1 ─ RENDER ENVIRONMENT VARIABLES
Paste ALL of these into your Render web service → Environment tab:

  SECRET_KEY       = {SECRET_KEY}
  DATABASE_URL     = {NEON_DATABASE_URL}
  ALLOWED_HOSTS    = {RENDER_DOMAIN}
  DEBUG            = False
  ADMIN_USERNAME   = {ADMIN_USERNAME}
  ADMIN_EMAIL      = {CUSTOMER_EMAIL}
  ADMIN_PASSWORD   = {ADMIN_PASSWORD}
  GEMINI_API_KEY   = {GEMINI_API_KEY}
  FRESH_INSTALL    = false

──────────────────────────────────────────────────────────────────────
STEP 2 ─ CREDENTIALS TO HAND OVER TO CUSTOMER
Send these to the customer after the deployment succeeds:

  App URL          : https://{RENDER_DOMAIN}
  Username         : {ADMIN_USERNAME}
  Password         : {ADMIN_PASSWORD}
  Support email    : (your email here)

⚠️  Tell the customer to change their password immediately after first login.
──────────────────────────────────────────────────────────────────────
STEP 3 ─ CHECKLIST (complete in order)
  [ ] Create Neon account & project for customer → copy DATABASE_URL
  [ ] Go to Render → New Web Service → connect GitHub repo
  [ ] Paste all environment variables above
  [ ] Set Build Command  : bash ./build.sh
  [ ] Set Start Command  : gunicorn agency_crm.wsgi --log-file -
  [ ] Click Deploy
  [ ] Wait for build to finish (2–4 minutes)
  [ ] Visit https://{RENDER_DOMAIN}/admin/ → confirm login works
  [ ] Send Step 2 credentials to customer
  [ ] Save this file somewhere safe as {slug}_credentials.txt
══════════════════════════════════════════════════════════════════════
"""

print(output)

# Save to a file automatically
filename = f"{slug}_deployment_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt"
with open(filename, "w") as f:
    f.write(output)

print(f"✅ Saved to: {filename}")
print("   Keep this file safe — it contains passwords!")
