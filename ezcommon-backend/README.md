# Backend Deployment

FastAPI backend service for document parsing and form filling.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn auth_api:app --reload --host 0.0.0.0 --port 8000
```

## Production (Systemd)

```bash
sudo cp systemd/ezcommon-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ezcommon-backend
```

## Commands

```bash
sudo systemctl status ezcommon-backend   # Check status
sudo journalctl -u ezcommon-backend -f   # View logs
sudo systemctl restart ezcommon-backend  # Restart
```
