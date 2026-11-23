"""Train the SENTINELFLOW ML ensemble using configured paths."""
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate synthetic data if needed and train the hybrid detection ensemble."

    def add_arguments(self, parser):
        parser.add_argument("--regenerate", action="store_true")

    def handle(self, *args, **options):
        from apps.detection.services import sync_model_metadata
        from ml.train import train

        metadata = train(
            settings.BASE_DIR / "data", settings.ML_ARTIFACT_DIR,
            regenerate=options["regenerate"],
        )
        run = sync_model_metadata()
        self.stdout.write(self.style.SUCCESS(
            f"Training complete: {metadata['samples']} samples, accuracy {metadata['accuracy']:.3f}."
        ))
        self.stdout.write(f"Active model run: {run.model_name if run else 'none'}")
