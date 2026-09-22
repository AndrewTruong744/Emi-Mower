import firebase_admin
from firebase_admin import credentials

from src.config.settings import settings


def initialize_backend_auth():
    # The public API and repository layers can run without Firebase.  This is
    # intentionally opt-in so production still fails fast on bad credentials.
    if settings.FIREBASE_DISABLED:
        return None

    try:
        # If already initialized, fetch the existing default application instance
        return firebase_admin.get_app()
    except ValueError:
        # ADC honors GOOGLE_APPLICATION_CREDENTIALS, which the local Docker
        # overlay points at its read-only mounted ADC file. It also supports
        # local gcloud credentials and attached workload identity in deployment.
        return firebase_admin.initialize_app(
            credential=credentials.ApplicationDefault()
        )
