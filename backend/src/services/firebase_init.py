import os

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
        # Initialize a clean, default server instance
        current_dir = os.path.dirname(os.path.abspath(__file__))
        service_account_path = os.path.abspath(
            os.path.join(current_dir, "..", "..", "service-account.json")
        )
        cred = credentials.Certificate(service_account_path)
        return firebase_admin.initialize_app(credential=cred)
