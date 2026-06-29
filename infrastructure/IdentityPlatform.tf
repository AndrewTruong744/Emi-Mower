# 1. Enable the required GCP Service API for Identity Platform
resource "google_project_service" "identity_platform_api" {
  project            = "emi-mower"
  service            = "identitytoolkit.googleapis.com"
  disable_on_destroy = false
}

# 2. Initialize the core Identity Platform configuration for your project
resource "google_identity_platform_config" "default" {
  project    = google_project_service.identity_platform_api.project
  depends_on = [google_project_service.identity_platform_api]

  # Enables standard sign-in configurations (Email/Password, etc. if desired)
  sign_in {
    allow_duplicate_emails = false
    
    email {
      enabled           = true
      password_required = true
    }
  }
}

# 3. Configure Google SSO (OIDC/OAuth Provider)
resource "google_identity_platform_default_supported_idp_config" "google_sso" {
  project    = google_identity_platform_config.default.project
  idp_id     = "google.com" # Must be exactly google.com for default provider
  enabled    = true
  client_id  = var.google_client_id
  client_secret = var.google_client_secret
}