# To Install

## Gcloud CLI
- sudo apt-get update
- sudo apt-get install -y apt-transport-https ca-certificates gnupg curl
- curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
- echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
- sudo apt-get update && sudo apt-get install -y google-cloud-cli
- gcloud init
- set Emi-Mower as main project
- gcloud auth application-default login

## Terraform CLI
- wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
- echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
- sudo apt update && sudo apt install terraform
- terraform init

## Service Account
- go to IAM and Admin
- create a service account with necessary permissions
- create a Json key and import it to your project