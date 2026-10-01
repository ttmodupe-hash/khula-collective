# Railway Deployment Guide

## Prerequisites

- [Railway](https://railway.app) account
- GitHub account with this repo forked
- (Optional) Custom domain

## Step 1: Fork the Repository

1. Go to https://github.com/ttmodupe-hash/khula-collective
2. Click **Fork** in the top-right corner
3. This creates your own copy under your GitHub account

## Step 2: Create Railway Project

1. Log in to [Railway](https://railway.app)
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Choose your forked `khula-collective` repository
5. Railway will auto-detect the `railway.toml` and `Dockerfile`

## Step 3: Configure Environment Variables

In your Railway project dashboard:

1. Go to **Variables** tab
2. Add the following:

```
# Required (auto-set by Railway)
PORT=8501

# Payment Gateway (optional — needed for online payments)
PAYFAST_MERCHANT_ID=your_merchant_id
PAYFAST_MERCHANT_KEY=your_merchant_key
PAYFAST_PASSPHRASE=your_passphrase

# Ozow (optional — needed for Instant EFT)
OZOW_SITE_CODE=your_site_code
OZOW_API_KEY=your_api_key
```

## Step 4: Deploy

Railway auto-deploys on every push to `main`. For manual deploy:

1. Go to your project in Railway
2. Click **Deploy** in the top-right
3. Wait for build (~2-3 minutes)
4. Click the generated domain to view your app

## Step 5: Add Custom Domain

1. In Railway dashboard, go to **Settings** → **Domains**
2. Click **Custom Domain**
3. Enter your domain (e.g., `app.khulacollective.co.za`)
4. Railway provides a CNAME target
5. Add the CNAME record in your DNS provider
6. Wait for SSL certificate (auto-provisioned)

## Step 6: Enable GitHub Auto-Deploy

1. Go to **Settings** in Railway
2. Under **Environment**, enable **Auto-Deploy**
3. Now every push to `main` auto-deploys

## Step 7: GitHub Actions CI/CD (Optional)

Add a `RAILWAY_TOKEN` secret to your GitHub repo:

1. In Railway: **Settings** → **Tokens** → **New Token**
2. Copy the token
3. In GitHub: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
4. Name: `RAILWAY_TOKEN`, Value: your token

Now pushes to `main` auto-deploy via GitHub Actions.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check `railway.toml` and `Dockerfile` are present |
| App won't start | Check `PORT` env var is set |
| Database lost | Add a Railway Volume and mount to `/app` |
| Payments not working | Verify PayFast/Ozow credentials |

## Monitoring

Railway provides built-in:
- **Logs** — real-time application logs
- **Metrics** — CPU, memory, network usage
- **Deployments** — rollback to previous versions

## Scaling

Railway auto-scales based on traffic. For manual scaling:
1. Go to **Settings** → **Resources**
2. Adjust CPU and memory limits
