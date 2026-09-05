resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

locals {
  # Bucket names are globally unique. Change this prefix if another project
  # already owns either name before applying.
  cutout_bucket_prefix = "emi-mower-cutouts"
}

resource "google_storage_bucket" "cutouts_sandbox" {
  name                        = "${local.cutout_bucket_prefix}-sandbox"
  location                    = "US-EAST1" # GCP canonical form of us-east-1.
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }

  depends_on = [google_project_service.storage]
}

resource "google_storage_bucket" "cutouts_prod" {
  name                        = "${local.cutout_bucket_prefix}-prod"
  location                    = "US-EAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  lifecycle_rule {
    condition { age = 365 }
    action { type = "Delete" }
  }

  depends_on = [google_project_service.storage]
}

output "cutout_sandbox_bucket_name" {
  value       = google_storage_bucket.cutouts_sandbox.name
  description = "Use as GCS_CUTOUT_BUCKET for sandbox and test deployments."
}

output "cutout_prod_bucket_name" {
  value       = google_storage_bucket.cutouts_prod.name
  description = "Use as GCS_CUTOUT_BUCKET for production deployments."
}
