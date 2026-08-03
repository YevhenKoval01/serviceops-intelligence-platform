output "resource_group_name" {
  description = "Resource group containing the ServiceOps workload."
  value       = azurerm_resource_group.main.name
}

output "container_registry_name" {
  description = "Azure Container Registry used by the deployment workflow."
  value       = azurerm_container_registry.main.name
}

output "container_registry_login_server" {
  description = "Login server containing the three application images."
  value       = azurerm_container_registry.main.login_server
}

output "frontend_url" {
  description = "Public HTTPS URL for the operator interface."
  value       = "https://${azurerm_container_app.frontend.latest_revision_fqdn}"
}

output "backend_internal_fqdn" {
  description = "Container Apps internal ingress hostname for Spring Boot."
  value       = azurerm_container_app.backend.latest_revision_fqdn
}

output "eventhubs_namespace" {
  description = "Event Hubs namespace providing the Kafka-compatible endpoint."
  value       = azurerm_eventhub_namespace.main.name
}

output "postgres_fqdn" {
  description = "Private PostgreSQL Flexible Server hostname."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "operator_username" {
  description = "Bootstrap operator username."
  value       = var.operator_username
}

output "operator_password" {
  description = "Generated bootstrap operator password. Rotate through Terraform when required."
  value       = random_password.operator.result
  sensitive   = true
}

output "viewer_username" {
  description = "Bootstrap viewer username."
  value       = var.viewer_username
}

output "viewer_password" {
  description = "Generated bootstrap viewer password. Rotate through Terraform when required."
  value       = random_password.viewer.result
  sensitive   = true
}
