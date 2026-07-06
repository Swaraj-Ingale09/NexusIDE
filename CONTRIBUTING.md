# Contributing to NexusIDE

Thank you for your interest in contributing to NexusIDE! This guide will help you get started.

## Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/yourusername/NexusIDE.git
cd NexusIDE

# 2. Setup
cp .env.example .env
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. Database
python manage.py migrate
python manage.py create_admin

# 4. Run
python manage.py runserver
cd frontend && npm install && npm run dev
```

## Development Workflow

1. Create a feature branch: `git checkout -b feature/amazing-feature`
2. Make your changes
3. Run linters: `flake8 apps/ && black apps/`
4. Run tests: `python manage.py test`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

## Code Standards

- **Python**: PEP 8, Black formatter, 120 char line limit
- **JavaScript/React**: ESLint + Prettier
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)

## Project Structure

```
NexusIDE/
├── apps/
│   ├── users/          # Auth, profiles, admin
│   ├── compiler/       # IDE, code execution, AI
│   ├── community/      # Social features
│   ├── projects/       # Project management
│   └── problems/       # Competitive programming
├── config/             # Django settings, URLs, Celery
├── frontend/           # React + Vite
├── static/             # Built frontend assets
└── templates/          # Django templates
```

## Testing

```bash
# Backend
python manage.py test

# Frontend
cd frontend && npm test

# Coverage
cd frontend && npm run test:coverage
```

## Reporting Issues

- Use GitHub Issues
- Include steps to reproduce
- Include OS/browser info
- Include error messages/screenshots

## Code of Conduct

Be respectful, inclusive, and constructive. We're here to learn and build together.
