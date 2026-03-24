from django.apps import AppConfig


class DocumentsParserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents_parser"
    verbose_name = "Documents Parser"

    def ready(self):
        """Import signals when app is ready."""
        import apps.documents_parser.signals  # noqa: F401
