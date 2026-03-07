# Contributing to SteerPlane

Thank you for your interest in contributing to SteerPlane! We welcome contributions from everyone.

## 🚀 Getting Started

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/<your-username>/SteerPlane.git
   cd SteerPlane
   ```
3. **Set up the development environment** (see below)
4. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/my-feature
   ```

## 🛠️ Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 17 (or SQLite for development)

### SDK

```bash
cd sdk
pip install -e ".[dev]"
```

### API Server

```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

## 📐 Code Style

### Python (SDK & API)
- Follow PEP 8
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Maximum line length: 100 characters

### TypeScript (Dashboard)
- Use TypeScript strict mode
- Use functional components with hooks
- Follow the existing component patterns

## 🧪 Testing

```bash
# SDK tests
cd sdk
pytest

# API tests
cd api
pytest

# Dashboard lint
cd dashboard
npm run lint
```

## 📝 Pull Request Process

1. **Write clear commit messages** — use conventional commits:
   - `feat: add webhook notifications`
   - `fix: correct cost calculation rounding`
   - `docs: update SDK usage guide`

2. **Update documentation** if your change affects the public API

3. **Add tests** for new features

4. **Ensure CI passes** — all tests and lints must pass

5. **Request a review** from a maintainer

## 🐛 Reporting Bugs

Open an issue with:
- **Description** of the bug
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Environment** (OS, Python version, Node version)

## 💡 Feature Requests

Open an issue with:
- **Problem** you're trying to solve
- **Proposed solution**
- **Alternatives** you've considered

## 📁 Project Structure

```
SteerPlane/
├── sdk/            # Python SDK (@guard decorator, telemetry, cost tracking)
├── api/            # FastAPI backend (REST API, database)
├── dashboard/      # Next.js monitoring dashboard
├── examples/       # Example agent integrations
├── docs/           # Documentation
└── scripts/        # Setup and utility scripts
```

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
