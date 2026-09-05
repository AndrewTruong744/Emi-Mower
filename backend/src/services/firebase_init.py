import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials


def initialize_backend_auth():
    # The public API and repository layers can run without Firebase.  This is
    # intentionally opt-in so production still fails fast on bad credentials.
    if os.getenv("FIREBASE_DISABLED", "").lower() == "true":
        return None

    try:
        # If already initialized, fetch the existing default application instance
        return firebase_admin.get_app()
    except ValueError:
        # ADC works with local gcloud credentials, service-account
        # impersonation, and the workload identity attached to Cloud Run.
        # The JSON-key path is retained only as an explicit fallback.
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        cred = (
            credentials.Certificate(Path(service_account_path))
            if service_account_path
            else credentials.ApplicationDefault()
        )
        return firebase_admin.initialize_app(credential=cred)
