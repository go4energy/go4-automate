# go4-automate - Port Configuration

## Production Ports

| Service       | Port | URL                              |
|---------------|------|----------------------------------|
| **Backend**   | 8002 | http://192.168.1.227:8002        |
| **Frontend**  | 8081 | http://192.168.1.227:8081        |

## Start Commands

```bash
# Backend starten (IMMER Port 8002!)
cd /opt/go4-automate/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Frontend starten
cd /opt/go4-automate/frontend
npm run dev -- --host 0.0.0.0 --port 8081
```

## Login Credentials

- **URL:** http://192.168.1.227:8081/login
- **Email:** team@go4.energy
- **Tenant:** go4energy

## Config Files

- Frontend API URL: `frontend/.env.local` -> `VITE_API_URL=http://192.168.1.227:8002/api`
- Backend Tenant: `backend/app/config.py` -> `default_tenant_id = "go4energy"`
