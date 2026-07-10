# 🇿🇦 Khula Collective

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.30+-ff4b4b.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://github.com/ttmodupe-hash/khula-collective/workflows/Khula%20Collective%20CI/CD/badge.svg)](https://github.com/ttmodupe-hash/khula-collective/actions)

> **"Khula"** — *to grow* in isiZulu

A **FICA-compliant investment club tracker** built for South African stokvels and collective investment groups. Manage up to 20 members, track monthly contributions, vote on investments, and grow your wealth together with AI-powered insights.

![Khula Collective Dashboard](https://via.placeholder.com/800x400/0a0a0a/00b894?text=Khula+Collective+Dashboard)

---

## Features

| Feature | Description | Status |
|---------|-------------|--------|
| 📊 **Dashboard** | Real-time collective pot balance, growth charts, 12-month projections | ✅ |
| 🤖 **AI Advisor** | SA market-aware investment recommendations with risk analysis | ✅ |
| 🗳️ **Member Voice** | Democratic voting on investment decisions (60% threshold) | ✅ |
| 📜 **Constitution** | Digital constitution with electronic signature | ✅ |
| 👥 **Member Directory** | View all members, contribution leaderboard, FICA status | ✅ v2.0 |
| 🔔 **Notifications** | In-app alerts for announcements, payments, votes | ✅ v2.0 |
| 📈 **Reports** | Contribution heatmaps, participation rates, investment tracking | ✅ v2.0 |
| 🔐 **Admin Panel** | Member management, exports, FICA compliance, broadcasts | ✅ v2.0 |
| 💬 **WhatsApp** | Share summaries and join group chat | ✅ v2.0 |
| 🌓 **Theme Toggle** | Dark/Light mode with persistent preference | ✅ v2.0 |
| 📱 **Mobile First** | Bottom nav, swipeable tabs, touch-optimized | ✅ v2.0 |
| 🧾 **FICA Ready** | Built-in compliance tracking for regulatory requirements | ✅ |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit (Python) |
| **Styling** | Custom CSS with dark theme |
| **Charts** | Plotly, Matplotlib |
| **Data** | Pandas, NumPy |
| **Database** | SQLite (auto-setup) |
| **Auth** | Session-based with SHA-256 |
| **AI** | Rule-based with SA market data |
| **CI/CD** | GitHub Actions |
| **Container** | Docker + Docker Compose |

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone repository
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

# Run app
streamlit run app.py
```

Open your browser at `http://localhost:8501`

### Docker Setup

```bash
# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| **Admin** | `admin` | `admin123` |
| **Member** | `siphoo` | `password1` |

---

## Deployment

### Streamlit Cloud (Recommended)

1. Connect your GitHub repo at [share.streamlit.io](https://share.streamlit.io)
2. Select `ttmodupe-hash/khula-collective`
3. Deploy automatically on every push

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STREAMLIT_SERVER_HEADLESS` | Yes | Run without browser |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | No | Disable telemetry |
| `STREAMLIT_API_KEY` | No | For GitHub Actions deploy |

---

## Project Structure

```
khula-collective/
├── app.py                          # Main application (3,247 lines)
├── requirements.txt                # Python dependencies
├── runtime.txt                     # Python version
├── packages.txt                    # System dependencies
├── Dockerfile                      # Container definition
├── docker-compose.yml              # Local orchestration
├── .streamlit/
│   ├── config.toml                 # Streamlit configuration
│   └── secrets.toml.example        # Secrets template
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD pipeline
├── README.md                       # This file
├── DEPLOYMENT.md                   # Deployment guide
├── CHANGELOG.md                    # Version history
├── CONTRIBUTING.md                 # Contributor guide
└── LICENSE                         # MIT License
```

---

## Roadmap

### v2.1.0 (Planned)
- [ ] Email & SMS notifications
- [ ] PDF report generation
- [ ] FICA document upload
- [ ] Calendar integration

### v3.0.0 (Future)
- [ ] Multi-club support
- [ ] Real-time market data
- [ ] Mobile app (React Native)
- [ ] Bank integrations

See [CHANGELOG.md](CHANGELOG.md) for full history.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Quick start for contributors:

```bash
git checkout -b feat/your-feature
# Make changes
git commit -m "feat: add amazing feature"
git push origin feat/your-feature
# Open Pull Request
```

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) file.

---

## Acknowledgments

- Built with pride for the South African stokvel community
- Inspired by traditional Ubuntu principles of collective prosperity
- Powered by [Streamlit](https://streamlit.io) and open-source software

---

**Khula Collective Team** 🇿🇦

*Building Wealth Together*

[Report Bug](https://github.com/ttmodupe-hash/khula-collective/issues) · [Request Feature](https://github.com/ttmodupe-hash/khula-collective/issues)
