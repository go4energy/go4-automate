"""Custom exception classes for the application."""


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, id: int | str):
        super().__init__(
            message=f"{resource} mit ID {id} nicht gefunden",
            status_code=404,
        )


class DuplicateError(AppError):
    """Duplicate resource."""

    def __init__(self, resource: str, field: str):
        super().__init__(
            message=f"{resource} mit diesem {field} existiert bereits",
            status_code=409,
        )


class ExternalServiceError(AppError):
    """Error communicating with an external service."""

    def __init__(self, service: str, detail: str = ""):
        super().__init__(
            message=f"Fehler bei {service}: {detail}",
            status_code=502,
        )


class ValidationError(AppError):
    """Business logic validation error."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)


class AuthenticationError(AppError):
    """Authentication failed."""

    def __init__(self, message: str = "Nicht authentifiziert"):
        super().__init__(message=message, status_code=401)


class ForbiddenError(AppError):
    """Access forbidden."""

    def __init__(self, message: str = "Keine Berechtigung"):
        super().__init__(message=message, status_code=403)
