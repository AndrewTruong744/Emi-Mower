terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

# Replace this with your actual GCP Project ID from `gcloud config get-value project`
provider "google" {
  project = "emi-mower"
  region  = "us-central1"
}