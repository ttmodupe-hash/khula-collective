# Khula Collective — Deployment Guide

Complete deployment instructions for the Khula Collective investment club platform.

---

## Table of Contents

- [Streamlit Cloud (Recommended)](#streamlit-cloud-recommended)
- [Docker Deployment](#docker-deployment)
- [Heroku Deployment](#heroku-deployment)
- [Local Development](#local-development)
- [Database Setup](#database-setup)
- [Post-Deployment Checklist](#post-deployment-checklist)
- [Troubleshooting](#troubleshooting)
- [Updating the App](#updating-the-app)

---

## Streamlit Cloud (Recommended)

The easiest way to deploy Khula Collective.

### Prerequisites

- GitHub account
- Streamlit Cloud account (free at [streamlit.io/cloud](https://streamlit.io/cloud))

### Step 1: Connect Repository

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `ttmodupe-hash/khula-collective`
5. Branch: `main`
6. Main file path: `app.py`
7. Click "Deploy"

### Step 2: Configure Secrets

1. In your app dashboard, click "Settings" (⚙️)
2. Go to "Secrets" section
3. Add your secrets in TOML format:

```toml
[auth]
jwt_secret = "your-super-secret-key"

[admin]
username = "admin"
password = "your-secure-password"
```

### Step 3: Verify Deployment

- Your app will be available at: `https://khula-collective.streamlit.app`
- Check the logs in the Streamlit Cloud dashboard
- Test login with demo credentials

### Step 4: Enable Auto-Deploy (GitHub Actions)

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:
- Runs linting and security checks on every push
- Validates the app starts correctly
- Posts deployment status as commit comments

To enable:
1. Go to your GitHub repository → Settings → Secrets
2. Add `STREAMLIT_API_KEY` (get from Streamlit Cloud settings)
3. Add `STREAMLIT_APP_URL` (your app URL)
4. (Optional) Add `SLACK_WEBHOOK_URL` for failure notifications

---

## Docker Deployment

For self-hosted or production deployments.

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+ (optional)

### Quick Start

```bash
# Clone repository
git clone https://github.com/ttmodupe-hash/khula-collective.git
cd khula-collective

# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f

# Access app
open http://localhost:8501
```

### Manual Docker Build

```bash
# Build image
docker build -t khula-collective:v2.0.0 .

# Run container
docker run -d \
  --name khula-collective \
  -p 8501:8501 \
  -v khula-data:/app/data \
  --restart unless-stopped \
  khula-collective:v2.0.0

# Check health
docker ps
docker logs khula-collective
```

### Production with Nginx

Uncomment the nginx service in `docker-compose.yml`:

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - khula-app
```

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://khula-app:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

---

## Heroku Deployment

### Prerequisites

- Heroku CLI installed
- Heroku account

### Steps

```bash
# Login to Heroku
heroku login

# Create app
heroku create khula-collective

# Add buildpacks
heroku buildpacks:add heroku/python

# Set environment variables
heroku config:set STREAMLIT_SERVER_HEADLESS=true
heroku config:set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Create Procfile
echo "web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0" > Procfile

# Deploy
git add .
git commit -m "Prepare for Heroku deployment"
git push heroku main

# Open app
heroku open

# View logs
heroku logs --tail
```

---

## Local Development

### Standard Setup

```bash
# Clone repo
git clone https://github.com/ttmodupe-hash/khula-collective.git
cd khula-collective

# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy secrets template
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your values

# Run app
streamlit run app.py
```

### Using Make (if available)

```bash
make setup    # Install dependencies
make run      # Run development server
make lint     # Run linter
make test     # Run tests
make docker   # Build Docker image
```

---

## Database Setup

### Automatic (Recommended)

The app automatically creates all required tables on first run. No manual setup needed.

### Tables Created

| Table | Purpose |
|-------|---------|
| `Users` | Member accounts and profiles |
| `Monthly_Contributions` | Contribution tracking |
| `Suggestions` | Investment suggestions and votes |
| `Announcements` | Admin broadcasts |
| `Investments` | Portfolio tracking |
| `Notifications` | User notifications |

### Manual Schema (if needed)

```bash
# Run schema file
sqlite3 khula_collective.db < khula_schema.sql

# Seed with demo data
python khula_seed_data.py
```

### Backup & Restore

```bash
# Backup
cp khula_collective.db backups/khula_$(date +%Y%m%d).db

# Restore
cp backups/khula_20260101.db khula_collective.db
```

---

## Post-Deployment Checklist

- [ ] App loads without errors
- [ ] Login works with demo credentials
- [ ] Dashboard shows correct data
- [ ] Constitution signing works
- [ ] Voting system functions
- [ ] Admin panel is admin-only
- [ ] Mobile view is responsive
- [ ] Theme toggle works
- [ ] Exports download correctly
- [ ] Notifications appear
- [ ] Database persists across restarts

---

## Troubleshooting

### App Won't Start

**Problem**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
pip install -r requirements.txt
```

### Database Errors

**Problem**: `sqlite3.OperationalError: no such table`

**Solution**: Delete the database file and restart — tables are auto-created:
```bash
rm khula_collective.db
streamlit run app.py
```

### Port Already in Use

**Problem**: `Address already in use` on port 8501

**Solution**:
```bash
# Find and kill process
lsof -ti:8501 | xargs kill -9

# Or use different port
streamlit run app.py --server.port 8502
```

### Permission Denied (Docker)

**Problem**: Cannot write to database

**Solution**:
```bash
# Fix permissions
sudo chown -R 1000:1000 ./data

# Or run with user
docker run -u $(id -u):$(id -g) ...
```

### Streamlit Cloud Build Fails

**Problem**: Build fails on Streamlit Cloud

**Solution**:
1. Check `requirements.txt` has no conflicting versions
2. Verify `runtime.txt` has supported Python version
3. Check Streamlit Cloud logs for specific errors
4. Ensure no local file paths in code

### GitHub Actions Fails

**Problem**: CI/CD pipeline fails

**Solution**:
1. Check Actions tab for error logs
2. Verify secrets are set in repository settings
3. Run locally first: `flake8 app.py`
4. Ensure `requirements.txt` is up to date

### Slow Performance

**Problem**: App is slow to load

**Solution**:
- Use `@st.cache_data` for expensive operations
- Reduce dataframe sizes
- Optimize database queries
- Consider upgrading Streamlit Cloud plan

---

## Updating the App

### Update via Git (Streamlit Cloud)

1. Push changes to `main` branch
2. Streamlit Cloud auto-deploys (if connected)
3. Or trigger manual deploy from dashboard

### Update via GitHub Actions

```bash
# Make changes
git add .
git commit -m "feat: add new feature"
git push origin main

# GitHub Actions will:
# 1. Lint and test
# 2. Deploy to Streamlit Cloud
# 3. Post status comment
```

### Update Docker Deployment

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up --build -d

# Or update specific service
docker-compose up --build -d khula-app
```

### Database Migrations

When updating to a new version:

1. **Backup first**:
   ```bash
   cp khula_collective.db backups/pre-update.db
   ```

2. **The app auto-migrates** — new columns are added automatically

3. **If manual migration needed**:
   ```bash
   sqlite3 khula_collective.db "ALTER TABLE Users ADD COLUMN new_field TEXT;"
   ```

---

## Support

- **GitHub Issues**: [github.com/ttmodupe-hash/khula-collective/issues](https://github.com/ttmodupe-hash/khula-collective/issues)
- **Email**: team@khula-collective.co.za
- **Documentation**: See README.md

---

**Khula Collective Team** 🇿🇦 | Building Wealth Together
