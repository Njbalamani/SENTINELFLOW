from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Refresh the DetectionModelRun record from trained artifact metadata."

    def handle(self, *args, **options):
        from apps.detection.services import sync_model_metadata

        run = sync_model_metadata()
        if run:
            self.stdout.write(self.style.SUCCESS(f"Synced {run.model_name} · {run.samples} samples"))
        else:
            self.stdout.write("No trained artifacts found. Run `python manage.py train_models`.")
