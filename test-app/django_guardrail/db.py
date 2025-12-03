import logging
from functools import wraps

from django.db.backends.utils import CursorWrapper

logger = logging.getLogger(__name__)

_original_execute = None
_original_executemany = None
_patched = False


def _check_sql(sql: str, params=None):
    """Check SQL query through guardrailv2 before execution."""
    from django_guardrail.client import guardrail_client

    guardrail_client.check_query(sql, params)


def patched_execute(self, sql, params=None):
    """Patched execute method that validates SQL through guardrailv2."""
    _check_sql(sql, params)
    return _original_execute(self, sql, params)


def patched_executemany(self, sql, param_list):
    """Patched executemany method that validates SQL through guardrailv2."""
    _check_sql(sql, param_list[0] if param_list else None)
    return _original_executemany(self, sql, param_list)


def patch_database_wrapper():
    """Monkey-patch Django's CursorWrapper to intercept all SQL queries."""
    global _original_execute, _original_executemany, _patched

    if _patched:
        return

    _original_execute = CursorWrapper.execute
    _original_executemany = CursorWrapper.executemany

    CursorWrapper.execute = patched_execute
    CursorWrapper.executemany = patched_executemany

    _patched = True
    logger.info("Django Guardrail: Database wrapper patched successfully")


def unpatch_database_wrapper():
    """Restore original Django CursorWrapper methods."""
    global _original_execute, _original_executemany, _patched

    if not _patched:
        return

    if _original_execute:
        CursorWrapper.execute = _original_execute
    if _original_executemany:
        CursorWrapper.executemany = _original_executemany

    _patched = False
    logger.info("Django Guardrail: Database wrapper unpatched")
