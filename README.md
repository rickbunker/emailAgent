# Email Agent – Asset Document Management

An asynchronous Python 3.11+ system that watches corporate mailboxes (Gmail and Microsoft 365), classifies incoming attachments, runs security checks, and files documents to the correct asset folders – all while persisting knowledge in Qdrant for fast semantic search.

## Key Capabilities

• Email connectors for Gmail & Microsoft Graph
• Attachment validation → ClamAV scan → duplicate detection (SHA-256)
• AI-powered document categorisation & asset matching
• Qdrant vector storage for assets, sender mappings, and processing history
• Flask web UI for dashboards and manual review
• Fully typed, logged, and PEP-8 compliant (enforced by `pre-commit`)

---

## Quick-start

```bash
# 1) Install dependencies (runtime + dev)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# 2) Start services (local workstation)
# ‑ ClamAV
brew install clamav            # or apt-get install clamav
freshclam                      # update definitions
# ‑ Qdrant
docker run -p 6333:6333 qdrant/qdrant

# 3) Launch the web UI
python app.py                  # -> http://localhost:5001
```

Authentication setup details live in:
• `docs/MSGRAPH_SETUP.md` for Microsoft 365
• `docs/GMAIL_SETUP.md` for Gmail

---

## Minimal Usage Example

```python
from src.agents.asset_document_agent import AssetDocumentAgent
from src.utils.logging_system import get_logger

logger = get_logger(__name__)
agent = AssetDocumentAgent()

attachment = {
    "filename": "Q4_Rent_Roll.xlsx",
    "content": open("Q4_Rent_Roll.xlsx", "rb").read(),
}

email_ctx = {
    "sender_email": "manager@property.com",
    "subject": "December rent roll – 123 Main St.",
    "body": "Monthly tenant payment summary attached",
}

result = await agent.enhanced_process_attachment(attachment, email_ctx)
logger.info("Processed → %s, confidence %.2f", result.status, result.confidence)
```

---

## Project Layout (abridged)

```
emailAgent/
│  app.py               # Flask entry-point
│  pyproject.toml       # Build metadata
├─ src/
│  ├─ agents/           # Core AI agents (document, spam, contact)
│  ├─ email_interface/  # Gmail & Graph connectors
│  ├─ memory/           # Qdrant helpers & abstractions
│  ├─ utils/            # Config & logging framework
│  └─ web_ui/           # Flask blueprints & templates
└─ tests/               # Pytest suite (fast, no external calls)
```

---

## Development

The repository ships with a ready-to-go tool-chain:

• **Black + Isort** – automatic formatting
• **Ruff** – lint & simpler autofix
• **Mypy** – static type checking
• **Bandit / Detect-Secrets** – security scans
• **Pre-commit** – runs the whole stack on every commit / CI push

Set it up once:

```bash
pre-commit install          # git commit will now refuse on violations
```

Detailed guidelines live in `docs/CODING_STANDARDS.md`.

---

## Testing

Pytest fixtures spin up the Flask app in-process so tests complete in <2 s and require **no** live email or Qdrant.

```bash
pytest -q                     # run all tests
```

For longer integration runs (processing real mailboxes) see scripts under `scripts/`.

---

## Contributing

1. Fork & clone the repo.
2. Activate the venv and install dev deps.
3. Ensure `pre-commit` passes (`pre-commit run --all-files`).
4. Add type hints, Google-style docstrings, and tests for new features.
5. Open a PR – the CI pipeline will verify lint, type-check, tests, and security scans.

---

## License

Copyright 2025 Inveniam Capital Partners, LLC and Rick Bunker.
Internal use only.
