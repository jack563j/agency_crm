# 🚀 Agency CRM — Customer Onboarding Guide
### How to deploy a fresh copy for every new customer (Option 2: One instance per customer)

---

> **Time required per customer:** ~20 minutes  
> **Cost per customer:** ₹0 (using free tiers)  
> **Tools you need:** A browser, this guide, and the `new_customer.py` script

---

## Overview — What You'll Do

Each paying customer gets their **own private copy** of the app:

```
Customer A → acme-crm.onrender.com  →  Neon DB (Account A)
Customer B → techco-crm.onrender.com →  Neon DB (Account B)
You        → your-crm.onrender.com  →  Neon DB (Your account)
```

They never share data. If one customer deletes something, it doesn't affect anyone else.

---

## Step 1 — Create a Neon Database for the Customer

> Neon gives **one free project per account**. So you need either:
> - A new Neon account per customer (using their email), OR
> - Ask the customer to create their own Neon account and paste you the DATABASE_URL

### Option A — Customer creates their own (recommended)

Send the customer this message:

> *"To set up your CRM, I need you to do one quick thing:*
> *1. Go to https://neon.tech and sign up for a free account*
> *2. Click 'Create Project' → name it anything (e.g. 'my-crm')*
> *3. Copy the connection string that looks like: `postgresql://user:pass@host/dbname?sslmode=require`*
> *4. Send that string to me — that's all I need!"*

### Option B — You create it (using a spare email)

1. Go to [https://neon.tech](https://neon.tech) and sign up with a new Gmail (e.g. `yourname+customer1@gmail.com`)
2. Click **Create Project** → name it `customer-name-crm`
3. Go to **Dashboard → Connection Details**
4. Copy the **Connection string** (it starts with `postgresql://...`)

---

## Step 2 — Run the Setup Script

On your Windows PC, open PowerShell in the project folder and run:

```powershell
cd C:\Users\91784\Documents\new\agency_crm
python customer_setup\new_customer.py
```

It will ask you 5 questions:

| Question | What to enter |
|---|---|
| Customer name | e.g. `Acme Digital` |
| Customer email | Their email address |
| Neon DATABASE_URL | The connection string from Step 1 |
| Render app URL | Leave blank for now — you'll fill this after Step 3 |
| Gemini API key | Your key (or the customer provides their own) |

> **Note:** Leave Render URL blank for now and run it again after Step 3 with the real URL. Or just type a placeholder and edit the file later.

The script saves a file like `acme_digital_deployment_20260903.txt` — **keep this safe**, it has the admin password.

---

## Step 3 — Deploy on Render

1. Go to [https://render.com](https://render.com) and log in
2. Click **New +** → **Web Service**
3. Under "Connect a repository", select your GitHub repo: `jack563j/agency_crm`
4. Fill in the settings:

| Field | Value |
|---|---|
| **Name** | `acme-crm` (use customer's business name, lowercase, no spaces) |
| **Region** | Singapore (closest to India) |
| **Branch** | `main` |
| **Build Command** | `bash ./build.sh` |
| **Start Command** | `gunicorn agency_crm.wsgi --log-file -` |
| **Instance Type** | Free |

5. Scroll down to **Environment Variables** and click **Add Environment Variable** for each line below (from your script output):

```
SECRET_KEY       → (paste from script)
DATABASE_URL     → (paste from script)
ALLOWED_HOSTS    → acme-crm.onrender.com
DEBUG            → False
ADMIN_USERNAME   → (paste from script)
ADMIN_EMAIL      → (paste from script)
ADMIN_PASSWORD   → (paste from script)
GEMINI_API_KEY   → (paste from script)
FRESH_INSTALL    → false
```

> ⚠️ **ALLOWED_HOSTS** must match the Render URL exactly. Render shows you the URL before deploying — it's at the top of the page.

6. Click **Create Web Service**

---

## Step 4 — Wait for Deployment

- Render takes **2–4 minutes** to build and deploy
- You'll see logs streaming — look for `Build complete!` at the end
- The URL at the top of the page will turn green when live

**If you see an error**, the most common causes are:
- Wrong `DATABASE_URL` — double-check from Neon
- Missing environment variable — check all 9 are set
- `ALLOWED_HOSTS` doesn't match the Render URL exactly

---

## Step 5 — Test the Deployment

1. Visit `https://acme-crm.onrender.com`

> ⚠️ **Free Render services sleep after 15 minutes of inactivity.** The first load after sleeping takes ~30–60 seconds. This is a known limitation of the free tier. Paid Render plans ($7/month) stay awake.

2. Log in with the credentials from your script output
3. Verify:
   - [ ] Dashboard loads correctly
   - [ ] Can create a Lead
   - [ ] AI Copilot responds (if Gemini API key is set)
   - [ ] Invoice PDF prints

---

## Step 6 — Hand Over to the Customer

Send the customer an email like this:

---

> **Subject:** Your Agency CRM is Live! 🎉
>
> Hi [Name],
>
> Your Agency CRM is ready! Here are your login details:
>
> 🌐 **App URL:** https://acme-crm.onrender.com  
> 👤 **Username:** admin_acme_digital  
> 🔑 **Password:** [from script]  
>
> **First thing to do:** Log in and change your password under the Django Admin panel.
>
> **Note:** The app may take 30–60 seconds to load on first open — this is normal on the free hosting plan. If you'd like instant loading, we can upgrade for an additional ₹600/month.
>
> For any questions, reply to this email.
>
> Best,  
> [Your name]

---

## Common Issues & Fixes

| Problem | Fix |
|---|---|
| App shows "Bad Request (400)" | `ALLOWED_HOSTS` env var doesn't match the Render URL |
| App shows "Server Error (500)" | Check Render logs — usually a wrong `DATABASE_URL` |
| Login doesn't work | Check `ADMIN_USERNAME` and `ADMIN_PASSWORD` were set before first deploy |
| AI Copilot not responding | `GEMINI_API_KEY` is missing or invalid |
| Page loads but looks broken | Missing `SECRET_KEY` or `DEBUG=True` accidentally |

---

## Upgrading a Customer Later

If a customer wants:

### Custom domain (e.g. `crm.acmedigital.in`)
1. Go to Render → their service → **Settings → Custom Domains**
2. Add their domain
3. They add a CNAME record in their DNS pointing to `acme-crm.onrender.com`
4. Update `ALLOWED_HOSTS` env var to include the new domain: `acme-crm.onrender.com crm.acmedigital.in`

### Always-on (no sleep on first load)
- Upgrade the Render service to **Starter plan** (~$7/month = ~₹600/month)
- You can charge the customer ₹600–₹999/month and it's covered

### More storage / bigger database
- Upgrade Neon to **Launch plan** ($19/month)
- Or the customer creates a paid Neon account themselves

---

## Your Profit Model (Reference)

| What you pay | What you charge | Your profit |
|---|---|---|
| Render Free | ₹999/month | ₹999 |
| Render Starter ($7) + Neon Free | ₹999/month | ~₹400 |
| Render Starter + Neon Launch ($19) | ₹1,999/month | ~₹700 |

> With 10 customers at ₹999/month = **₹9,990/month** recurring income.

---

## File & Folder Reference

```
agency_crm/
├── customer_setup/
│   ├── new_customer.py          ← Run this for each new customer
│   └── ONBOARDING_GUIDE.md     ← This file
├── build.sh                     ← Safe for production (data never wiped unless FRESH_INSTALL=true)
└── ...rest of the app
```

---

*Guide version: 1.0 | Last updated: September 2026*
