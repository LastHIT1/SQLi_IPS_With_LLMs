import logging
import os
from typing import Any

import httpx
from django.conf import settings

from django_guardrail.exceptions import GuardrailServiceError, SQLInjectionDetected

logger = logging.getLogger(__name__)


class GuardrailClient:
    """Client for communicating with guardrailv2 ML service."""

    def __init__(self):
        self.service_url = getattr(
            settings, "GUARDRAIL_SERVICE_URL", "http://guardrailv2:5001"
        )
        self.timeout = getattr(settings, "GUARDRAIL_TIMEOUT", 5.0)
        self.enabled = getattr(settings, "GUARDRAIL_ENABLED", True)
        self.fail_open = getattr(settings, "GUARDRAIL_FAIL_OPEN", False)

    def _is_skip_guardrail(self) -> bool:
        """Check if guardrail should be skipped (e.g., during migrations)."""
        return os.environ.get("SKIP_GUARDRAIL", "").lower() in ("1", "true", "yes")

    def check_query(self, sql: str, params: tuple | None = None) -> dict[str, Any]:
        """
        Send SQL query to guardrailv2 for validation.

        Args:
            sql: The SQL query string
            params: Query parameters (optional)

        Returns:
            Response from guardrailv2

        Raises:
            SQLInjectionDetected: If injection is detected
            GuardrailServiceError: If service is unavailable and fail_open is False
        """
        if not self.enabled or self._is_skip_guardrail():
            return {"allowed": True}

        query_text = sql
        if params:
            query_text = f"{sql} {params}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.service_url,
                    content=query_text.encode("utf-8"),
                    headers={
                        "Content-Type": "text/plain",
                        "X-Original-URI": "/sql-query",
                        "X-Original-Method": "POST",
                    },
                )

                if response.status_code == 200:
                    return {"allowed": True}

                if response.status_code == 403:
                    data = response.json()
                    raise SQLInjectionDetected(
                        message=f"SQL Injection detected: {data.get('threat_type', 'Unknown')}",
                        query=sql[:500],
                        confidence=data.get("confidence"),
                        threat_type=data.get("threat_type"),
                    )

                logger.warning(
                    f"Guardrailv2 returned unexpected status: {response.status_code}"
                )
                if self.fail_open:
                    return {"allowed": True}
                raise GuardrailServiceError(
                    f"Unexpected response from guardrailv2: {response.status_code}"
                )

        except httpx.RequestError as e:
            logger.error(f"Failed to connect to guardrailv2: {e}")
            if self.fail_open:
                return {"allowed": True}
            raise GuardrailServiceError(f"Cannot connect to guardrailv2: {e}") from e


guardrail_client = GuardrailClient()
