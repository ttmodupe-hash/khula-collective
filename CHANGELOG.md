# Changelog

All notable changes to the Khula Collective project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-07-11

### Major Release — Enhanced Investment Club Platform

### Added

#### Admin Panel
- Member management (add, edit, deactivate members)
- Contribution tracking and management
- Mark contributions as paid/unpaid with batch operations
- Export data to CSV and Excel (multi-sheet exports)
- Broadcast announcements with priority levels
- FICA compliance status tracking and toggling
- Investment portfolio management (add, update status)
- Admin-only dashboard with summary statistics

#### Member Directory
- Photo placeholder cards with member initials
- Member profiles with join dates and contribution stats
- FICA & Constitution status badges
- Contribution leaderboard with gold/silver/bronze highlighting
- FICA compliance summary table

#### Notifications System
- In-app notification bell with unread count badge
- Auto-generated announcements from admin broadcasts
- Type-based notifications (welcome, payment, vote, announcement)
- Mark individual or all notifications as read
- Persistent notification history

#### Reports & Analytics
- Contribution heatmap (monthly grid showing who paid when)
- Member participation rate bar chart
- Investment performance tracker with treemap visualization
- Monthly summary report with collection rate percentage
- Exportable report generation

#### Enhanced AI Advisor
- South African financial news feed (15+ simulated articles)
- Risk assessment quiz (5 questions generating investor profile)
- Compound interest calculator with projections
- Portfolio allocation visualizer (pie chart, treemap)
- Updated market indicators (Repo Rate, Prime, Inflation)

#### WhatsApp Integration
- Join WhatsApp group button
- Share investment summaries via WhatsApp link
- Contact admin via WhatsApp

#### Theme Toggle
- Dark/Light theme toggle
- Persistent theme preference
- Full CSS styling for both themes

#### Mobile UX Improvements
- Bottom navigation bar (responsive)
- Swipeable tabs throughout the app
- Pull-to-refresh simulation button
- Touch-optimized button sizes

### Infrastructure
- Full CI/CD pipeline with GitHub Actions
- Docker support with multi-stage production build
- Docker Compose for local development
- Comprehensive test suite structure
- Security scanning (bandit, safety)

### Documentation
- Complete README with badges and screenshots
- Deployment guide for multiple platforms
- Contributing guidelines
- Changelog (this file)
- MIT License

---

## [1.0.0] - 2026-02-11

### Initial Release

### Added
- Login system with admin and member roles
- Dashboard with collective pot balance display
- Growth over time chart with Plotly
- 12-month balance projection with AI analysis
- AI Investment Advisor with SA market awareness
  - RSA Retail Savings Bonds recommendations
  - Satrix Top 40 ETF recommendations
  - FNB Money Market Fund recommendations
- Member Voice voting system for investment decisions
- Digital Constitution with electronic signature
- Profile page with personal contribution tracking
- Payment history calendar view
- Mobile-first responsive design
- SQLite database with full schema
- Seed data for 20 members

---

## [Unreleased]

### Planned for v2.1.0
- [ ] Email notifications via SMTP
- [ ] SMS notifications via Twilio
- [ ] Automated monthly contribution reminders
- [ ] PDF report generation
- [ ] Member document upload (FICA docs)
- [ ] Investment return tracking with actual performance
- [ ] Calendar integration for meetings

### Planned for v3.0.0
- [ ] Multi-club support (manage multiple stokvels)
- [ ] Real-time market data integration
- [ ] Mobile app (React Native/Flutter)
- [ ] Blockchain-based transaction ledger
- [ ] AI-powered investment predictions
- [ ] Integration with South African banks

---

## How to Update

### For Contributors

When making changes, add your entry under the `[Unreleased]` section following this format:

```markdown
### Added
- New feature description

### Changed
- Change description

### Fixed
- Bug fix description

### Removed
- Removed feature description
```

### Release Process

1. Update version number in relevant files
2. Move `[Unreleased]` changes to a new version section
3. Add release date
4. Create a git tag: `git tag -a v2.0.0 -m "Release version 2.0.0"`
5. Push tag: `git push origin v2.0.0`
6. Create GitHub release with notes

---

**Khula Collective Team** | Building Wealth Together 🇿🇦
