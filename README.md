# 🇿🇦 Khula Collective v3.0

**South African Investment Club Platform** — Building Wealth Together

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

## What's New in v3.0

- **Payment Tracking** — Upload proof of payment, track arrears, see "How behind am I?"
- **Banking Integration** — PayFast & Ozow (Instant EFT) support
- **Member Progress Dashboard** — Visual progress bars, monthly breakdowns
- **Admin Payment Management** — Verify payments, send reminders, export reports
- **Payment Reminders** — Automated and manual reminder system
- **Railway-Ready** — One-click deploy with Docker

## Features

| Feature | Description |
|---------|-------------|
| 👤 Member Auth | Secure login with hashed passwords |
| 📊 My Progress | "How behind am I?" dashboard with arrears tracking |
| 📤 Proof Upload | Upload payment proof (PDF/PNG/JPG) |
| 💳 Instant Pay | PayFast & Ozow integration |
| 🏦 Bank Details | Save & manage bank account info |
| 👑 Admin Panel | Verify payments, view all arrears, send reminders |
| 📈 Analytics | Payment charts, member progress, investment tracking |
| 🔔 Notifications | In-app alerts for payments, verifications, announcements |
| 🤖 AI Advisor | Risk assessment & compound interest calculator |
| 📱 Mobile-First | Bottom navigation, responsive design |

## Quick Start (Local)

```bash
git clone https://github.com/ttmodupe-hash/khula-collective.git
cd khula-collective
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Member | `siphoo` | `password1` |

## Deploy on Railway

### Option 1: One-Click Deploy

1. Fork this repo
2. Create a [Railway](https://railway.app) account
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your forked repo
5. Railway auto-detects `railway.toml` and deploys

### Option 2: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up
```

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PORT` | Auto-set by Railway | Auto |
| `DATABASE_URL` | SQLite path (default: `khula_collective.db`) | No |
| `PAYFAST_MERCHANT_ID` | PayFast sandbox/live merchant ID | For payments |
| `PAYFAST_MERCHANT_KEY` | PayFast merchant key | For payments |
| `PAYFAST_PASSPHRASE` | PayFast passphrase | For payments |
| `OZOW_SITE_CODE` | Ozow site code | For Ozow |
| `OZOW_API_KEY` | Ozow API key | For Ozow |

## FNB API Integration (Future)

The app is architected to support FNB/Plaid/Yodlee banking integrations:

1. Add your API credentials as Railway environment variables
2. Enable bank linking in the Banking page
3. Members can link accounts for automatic payment confirmation

## Project Structure

```
khula-collective/
├── app.py                 # Main application
├── requirements.txt       # Python dependencies
├── Dockerfile             # Production container
├── railway.toml           # Railway deployment config
├── .streamlit/
│   └── config.toml        # Streamlit theme & settings
└── .github/workflows/
    └── railway-deploy.yml # Auto-deploy on push
```

## South African Banking Support

| Bank | Status | Method |
|------|--------|--------|
| FNB | Ready | Manual EFT + API placeholder |
| ABSA | Ready | Manual EFT |
| Nedbank | Ready | Manual EFT |
| Standard Bank | Ready | Manual EFT |
| Capitec | Ready | Manual EFT |
| PayFast | Active | Card payments |
| Ozow | Active | Instant EFT |

## License

MIT License — see [LICENSE](LICENSE)
