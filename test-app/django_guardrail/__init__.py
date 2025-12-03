"""
Django Guardrail - SQL Injection Detection Package

This package intercepts all SQL queries and validates them through
the guardrailv2 ML service before execution.
"""

default_app_config = "django_guardrail.apps.DjangoGuardrailConfig"

__version__ = "0.1.0"
