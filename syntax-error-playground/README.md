# 🚨 Syntax Error Playground (Benchmark Repository)

This repository is intentionally populated with diverse syntax errors across multiple languages and file types. It serves as a benchmark and playground for testing **SyntaxFixer Agentic AI**.

---

## 📊 Inventory of Broken Files & Errors

| File | Language | Injected Syntax Errors |
| :--- | :--- | :--- |
| `backend/app.py` | Python | Missing colons (`def`, `while`, `if`), unclosed parenthesis |
| `backend/models/user.py` | Python | Missing colons on class & method headers, missing comma in parameter list |
| `backend/utils/auth.py` | Python | Invalid `===` operator in Python, missing colon on `try` block |
| `backend/services/payment.py` | Python | Unmatched list comprehension bracket, unexpected indentation |
| `frontend/src/index.js` | JavaScript | Unclosed parenthesis in function parameter list, unexpected token |
| `frontend/src/api/client.js` | JavaScript | Semicolon instead of comma in object literal |
| `frontend/src/components/button.js` | JavaScript | Unmatched parentheses in arrow function callback |
| `package.json` | JSON | Trailing commas in arrays and objects |
| `tsconfig.json` | JSON | Trailing comma before closing brace |
| `.github/workflows/ci.yml` | YAML | Tab indentation character and missing colon on key |
| `docker-compose.yml` | YAML | Unclosed string quote in environment variable list |
| `scripts/migrate.py` | Python | Unterminated multiline docstring, missing colons |

---

## 🛠️ Testing with SyntaxFixer Agentic AI

### 1. Scan the Repository
```bash
syntax-agent scan syntax-error-playground
```

### 2. Run Autonomous Multi-Agent Repair
```bash
syntax-agent agentic syntax-error-playground --provider gemini
```

### 3. Dry-Run Mode (Preview Fixes without modifying files)
```bash
syntax-agent agentic syntax-error-playground --provider heuristic --dry-run
```
