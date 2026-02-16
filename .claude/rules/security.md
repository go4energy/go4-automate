# Security Rules

## NIEMALS
- **Secrets in Git** – alle Secrets in `.env`, `.env` ist in `.gitignore`
- **SQL String-Concatenation** – immer SQLAlchemy ORM oder parametrisierte Queries
- **eval() / exec()** – niemals User-Input ausführen
- **CORS `*`** – immer explizite Origins angeben
- **chmod 777** – minimale Berechtigungen, max 755 für Dirs, 644 für Files
- **Hardcoded Credentials** – alles über Environment Variables
- **API Keys im Frontend** – nur Backend darf Secrets kennen

## Config via Pydantic BaseSettings
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

## SQL – Nur ORM oder Parameter
```python
# RICHTIG – SQLAlchemy ORM
result = await db.execute(select(Lead).where(Lead.id == lead_id))

# RICHTIG – Parametrisiert
result = await db.execute(text("SELECT * FROM leads WHERE id = :id"), {"id": lead_id})

# FALSCH – String Concatenation
result = await db.execute(text(f"SELECT * FROM leads WHERE id = {lead_id}"))
```

## Input Validation
- ALLE externen Inputs über Pydantic Schemas validieren
- Niemals User-Input direkt in Queries/Commands verwenden
- File Uploads: Typ + Größe prüfen, niemals Original-Dateinamen verwenden

## Dependencies
- `pip audit` regelmäßig ausführen (mindestens vor jedem Release)
- `npm audit` regelmäßig ausführen
- Keine Packages mit bekannten Vulnerabilities

## CORS
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # NIEMALS ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## Docker
- Non-root User in allen Containern
- Keine `--privileged` Flag
- Secrets über Docker Secrets oder `.env` (nicht in docker-compose.yml)
