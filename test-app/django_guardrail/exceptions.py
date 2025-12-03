class SQLInjectionDetected(Exception):
    """Exception raised when SQL injection is detected by guardrailv2."""

    def __init__(
        self,
        message: str = "SQL Injection detected",
        query: str | None = None,
        confidence: float | None = None,
        threat_type: str | None = None,
    ):
        self.query = query
        self.confidence = confidence
        self.threat_type = threat_type
        super().__init__(message)


class GuardrailServiceError(Exception):
    """Exception raised when guardrailv2 service is unavailable."""

    pass
