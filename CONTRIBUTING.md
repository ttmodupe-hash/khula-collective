# Contributing to Khula Collective

Thank you for your interest in contributing to **Khula Collective**! We welcome contributions from the community and are excited to have you help us build the best investment club platform for South Africa.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Convention](#commit-convention)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)
- [Community](#community)

---

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to:

- Be respectful and inclusive in all interactions
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect different viewpoints and experiences
- Prioritize the community's best interests

Harassment, trolling, or abusive behavior will not be tolerated.

---

## Getting Started

### Prerequisites

- Python 3.11+
- pip or conda
- Git
- Docker (optional, for containerized development)

### Quick Start

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/khula-collective.git
cd khula-collective

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

---

## Development Setup

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or just Docker
docker build -t khula-collective .
docker run -p 8501:8501 khula-collective
```

### Environment Variables

Copy the secrets template:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your values
```

### Database

The app uses SQLite which is created automatically on first run. No manual setup required.

---

## Coding Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with these specifics:

- **Line length**: 120 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Single quotes for strings, double for docstrings
- **Imports**: Grouped as stdlib → third-party → local, alphabetically sorted

```python
# Good example
import os
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
```

### Streamlit Best Practices

- Use `st.session_state` for user authentication state
- Cache expensive computations with `@st.cache_data` or `@st.cache_resource`
- Use `st.experimental_fragment` for independent UI updates
- Keep callbacks lightweight
- Use `st.columns` and `st.container` for layout, not HTML hacks

```python
# Good example
@st.cache_data(ttl=300)
def get_member_data():
    return pd.read_sql("SELECT * FROM Users", conn)

# Use columns for layout
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Members", 20)
```

### Documentation

- All functions must have docstrings
- Complex logic needs inline comments
- Update README.md if adding features

```python
def calculate_projection(balance: float, months: int, rate: float) -> dict:
    """
    Calculate future balance projection with compound interest.
    
    Args:
        balance: Current total balance in Rands
        months: Number of months to project
        rate: Monthly interest rate as decimal (e.g., 0.007 for 0.7%)
    
    Returns:
        dict with 'projected_balance', 'total_interest', 'monthly_breakdown'
    """
    ...
```

---

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (formatting, semicolons, etc.) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `chore` | Build process, dependencies, etc. |

### Examples

```
feat(admin): add member export to Excel

fix(auth): resolve login redirect loop for admin users

docs(readme): update installation instructions for Windows

refactor(database): optimize contribution query with indexing
```

---

## Pull Request Process

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Test locally**:
   ```bash
   streamlit run app.py
   ```

4. **Commit** with conventional commit messages

5. **Push** to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```

6. **Open a Pull Request** against `main` branch

### PR Checklist

- [ ] Code follows style guidelines
- [ ] All functions have docstrings
- [ ] README updated if needed
- [ ] No hardcoded secrets or credentials
- [ ] Tested locally
- [ ] Commit messages follow convention
- [ ] PR description explains the changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Screenshots (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```

---

## Reporting Issues

### Bug Reports

Use this template:

```markdown
**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen.

**Screenshots**
If applicable.

**Environment:**
 - OS: [e.g. Windows 11]
 - Browser: [e.g. Chrome 120]
 - App Version: [e.g. 2.0.0]

**Additional context**
Any other information.
```

### Security Issues

**DO NOT** open public issues for security vulnerabilities. Email: security@khula-collective.co.za

---

## Feature Requests

We love feature ideas! To request a feature:

1. Check existing issues first
2. Open a new issue with label `enhancement`
3. Describe:
   - The problem you're trying to solve
   - Your proposed solution
   - Any alternatives considered

---

## Community

- **Discussions**: Use GitHub Discussions for questions and ideas
- **Issues**: Use GitHub Issues for bugs and feature requests
- **Email**: team@khula-collective.co.za

---

## Development Workflow Summary

```bash
# 1. Sync with upstream
git checkout main
git pull upstream main

# 2. Create feature branch
git checkout -b feat/my-feature

# 3. Make changes and commit
git add .
git commit -m "feat(scope): description"

# 4. Push and create PR
git push origin feat/my-feature
# Then open PR on GitHub
```

---

**Thank you for contributing to Khula Collective!** 🇿🇦

Together we're building wealth for South African communities.
