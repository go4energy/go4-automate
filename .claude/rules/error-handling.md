# Error Handling

## Python – Custom Exceptions
Definiert in `app/exceptions.py`:
```python
class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

class NotFoundError(AppError):
    def __init__(self, resource: str, id: int | str):
        super().__init__(f"{resource} mit ID {id} nicht gefunden", 404)

class DuplicateError(AppError):
    def __init__(self, resource: str, field: str):
        super().__init__(f"{resource} mit diesem {field} existiert bereits", 409)

class ExternalServiceError(AppError):
    def __init__(self, service: str, detail: str = ""):
        super().__init__(f"Fehler bei {service}: {detail}", 502)
```

## Python – Router Pattern
```python
from loguru import logger

@router.post("/", response_model=LeadResponse)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    try:
        service = LeadService(db)
        return await service.create(data)
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AppError as e:
        logger.error(f"AppError: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_lead")
        raise HTTPException(status_code=500, detail="Interner Serverfehler")
```

## Python – Service Pattern
Services werfen Custom Exceptions, fangen sie NICHT selbst:
```python
class LeadService:
    async def get_by_id(self, lead_id: int) -> Lead:
        lead = await self.db.get(Lead, lead_id)
        if not lead:
            raise NotFoundError("Lead", lead_id)
        return lead
```

## Python – Loguru
```python
from loguru import logger

logger.info("Lead erstellt: {lead_id}", lead_id=lead.id)
logger.warning("Rate limit erreicht für Tenant {tenant}")
logger.error("DB-Verbindung fehlgeschlagen: {err}", err=str(e))
logger.exception("Unerwarteter Fehler")  # inkl. Traceback
```

## Vue – Loading/Error State Pattern
Jede Komponente mit Datenladung MUSS haben:
```javascript
const loading = ref(false)
const error = ref(null)

async function loadData() {
  loading.value = true
  error.value = null
  try {
    // ... API Call
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}
```

Template:
```html
<div v-if="loading">Laden...</div>
<div v-else-if="error" class="text-red-600">{{ error }}</div>
<div v-else><!-- Content --></div>
```

## HTTP Status Codes Referenz
| Code | Bedeutung | Wann |
|------|-----------|------|
| 200 | OK | GET, PUT erfolgreich |
| 201 | Created | POST erfolgreich |
| 204 | No Content | DELETE erfolgreich |
| 400 | Bad Request | Validation-Fehler |
| 401 | Unauthorized | Nicht authentifiziert |
| 403 | Forbidden | Keine Berechtigung |
| 404 | Not Found | Resource nicht gefunden |
| 409 | Conflict | Duplikat |
| 422 | Unprocessable | Pydantic Validation |
| 500 | Internal Error | Unerwarteter Fehler |
| 502 | Bad Gateway | Externer Service Fehler |
