# Contributing to FastAPI-MCP 🤝

Thank you for your interest in contributing to **FastAPI-MCP**! We welcome bug reports, documentation enhancements, feature proposals, and community contributions.

To maintain production stability, code quality, and security, **direct commits to the `main` branch are strictly prohibited**. Every change must follow the Pull Request (Merge Request) review workflow and receive explicit approval from the repository maintainer (**@manavmehta2403**).

---

## 🚦 Contribution Workflow (Step-by-Step)

### 1. Fork and Clone the Repository
Do not push branches directly to the primary repository. Instead:
1. Click **Fork** on the top right of the GitHub repository (`https://github.com/manavmehta2403/fastapi-mcp`).
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/fastapi-mcp.git
   cd fastapi-mcp
   ```

### 2. Set Up Your Local Development Environment
We support both Poetry and standard pip virtual environments with Python 3.10+:

**Using Poetry (Recommended):**
```bash
poetry install
poetry run pytest tests/ -v
```

**Using Standard venv / pip:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[test]"
pytest tests/ -v
```

### 3. Create a Feature Branch
Always base your branch on the latest `main`:
```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/issue-description
```

### 4. Write Code & Add Automated Tests
- Maintain type hints (`typing` annotations).
- Add unit or integration tests for any new endpoints, decorators, or scanner features in `tests/`.
- Ensure all tests pass with zero warnings or failures:
  ```bash
  pytest tests/ -v
  ```

### 5. Submit a Pull Request (Merge Request)
1. Push your branch to your fork:
   ```bash
   git push -u origin feature/your-feature-name
   ```
2. Open a Pull Request targeting `manavmehta2403/fastapi-mcp` branch `main`.
3. Fill out the PR template with a clear explanation of your changes.

---

## 🛡️ Review, Testing, and Approval Process

Every submitted Pull Request must satisfy all of the following requirements before merging:

1. **Automated CI Test Suite**:
   - The GitHub Actions CI matrix automatically runs across **Python 3.10, 3.11, 3.12, and 3.13** on both Ubuntu and Windows.
   - All tests must pass (green checkmark).
2. **Owner Review & Code Approval**:
   - As enforced by the repository branch protection rules, every PR requires an official code review and approval from **@manavmehta2403**.
3. **No Direct Commits**:
   - Force pushes and direct pushes to `main` are rejected by branch protection.

---

## 💬 Questions or Bug Reports?
Feel free to open an Issue in the [Issue Tracker](https://github.com/manavmehta2403/fastapi-mcp/issues).
