# Python Code Rules

## Type Hints
Alle Funktionen MÜSSEN Type Hints haben – Parameter und Return:
```python
async def get_lead(lead_id: int, db: AsyncSession) -> LeadResponse:
    ...
```

## Funktionen
- Max **30 Zeilen** pro Funktion
- Max **3 Parameter** (außer bei Pydantic-Schemas als Input)
- Eine Funktion = eine Aufgabe

## Domain-basierte Struktur
Neue Features als eigenes Modul unter `app/`:
```
app/
  leads/
    __init__.py
    router.py      # FastAPI Router, nur HTTP-Logik
    schemas.py     # Pydantic Schemas
    service.py     # Business-Logik
    models.py      # SQLAlchemy Models (optional, oder in app/models/)
```

## FastAPI Router Pattern
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.leads.schemas import LeadCreate, LeadResponse
from app.leads.service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])

@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    service = LeadService(db)
    return await service.create(data)
```

## Pydantic Schema Pattern
```python
from pydantic import BaseModel, ConfigDict, EmailStr

class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    company: str | None = None

class LeadResponse(LeadCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

## Business-Logik
- **Services** enthalten die Logik, NIEMALS Router
- Router: HTTP Request → Service Call → HTTP Response
- Services: Validierung → DB/External Calls → Ergebnis
- Services werfen Custom Exceptions (AppError, NotFoundError etc.)

## Dependencies
```python
# Standard Dependencies
async def get_db() -> AsyncGenerator[AsyncSession, None]: ...
async def get_current_tenant(request: Request) -> str: ...
```

## Benennung
- `snake_case` für Variablen, Funktionen, Module, Dateien
- `PascalCase` für Klassen (Models, Schemas, Exceptions)
- `UPPER_SNAKE_CASE` für Konstanten
- Prefix `get_`, `create_`, `update_`, `delete_` für CRUD-Funktionen

## Async
- `async def` für alle I/O-Operationen (DB, HTTP, Redis, File)
- `def` nur für reine CPU-Berechnungen
- `await` niemals vergessen bei async Calls
