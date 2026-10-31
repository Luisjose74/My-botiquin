from django.apps import AppConfig


class BotiquinConfig(AppConfig):
    name = 'botiquin'

    def ready(self):
        import sys

        if "runserver" in sys.argv:
            from .scheduler import iniciar_scheduler

            iniciar_scheduler()
