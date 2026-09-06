# Infrastructure

This area contains cloud and Terraform-oriented infrastructure. Its existing
setup guidance is in
[`infrastructure/README.md`](../../infrastructure/README.md).

Infrastructure changes can affect fleet connectivity and storage. Document the
target environment, run the appropriate validation or plan, and require
explicit authorization before an apply. Keep credentials and local cloud
configuration out of Git.
