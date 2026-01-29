# Frontend Deployment

Next.js frontend application.

## Quick Start

```bash
npm install
npm run dev
```

## Production (Systemd)

```bash
npm run build
sudo cp systemd/ezcommon-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ezcommon-frontend
```

## Commands

```bash
sudo systemctl status ezcommon-frontend   # Check status
sudo journalctl -u ezcommon-frontend -f   # View logs
sudo systemctl restart ezcommon-frontend  # Restart
```

## Manual Start

```bash
npm run start -- -H 0.0.0.0 -p 3000
```
