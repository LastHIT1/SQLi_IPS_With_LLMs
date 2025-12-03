from django.apps import AppConfig


class DjangoGuardrailConfig(AppConfig):
    name = "django_guardrail"
    verbose_name = "Django Guardrail SQL Protection"

    def ready(self):
        from django_guardrail.db import patch_database_wrapper

        patch_database_wrapper()
