locals {
  resource_prefix = lower("${var.name_prefix}-${var.environment}")
  unique_suffix   = substr(md5("${data.azurerm_client_config.current.subscription_id}-${local.resource_prefix}"), 0, 8)
  base_name       = substr("${local.resource_prefix}-${local.unique_suffix}", 0, 40)
  compact_name    = substr(replace("${local.resource_prefix}${local.unique_suffix}", "-", ""), 0, 40)
  topics = toset([
    "serviceops.ticket.created.v1",
    "serviceops.ticket.prediction-completed.v1",
    "serviceops.ticket.invalid.v1",
  ])
  common_tags = merge(
    {
      application = "serviceops-intelligence-platform"
      environment = var.environment
      managed-by  = "terraform"
    },
    var.tags,
  )
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.base_name}"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.base_name}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.40.0.0/16"]
  tags                = local.common_tags
}

resource "azurerm_subnet" "container_apps" {
  name                 = "snet-container-apps"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.40.0.0/23"]

  delegation {
    name = "container-apps"

    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "postgres" {
  name                 = "snet-postgres"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.40.2.0/24"]

  delegation {
    name = "postgres-flexible-server"

    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "${local.base_name}.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "postgres-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.main.id
  resource_group_name   = azurerm_resource_group.main.name
  registration_enabled  = false
  tags                  = local.common_tags
}

resource "random_password" "postgres" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
  min_upper        = 2
}

resource "random_password" "jwt" {
  length  = 64
  special = false
}

resource "random_password" "operator" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
  min_upper        = 2
}

resource "random_password" "viewer" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_lower        = 2
  min_numeric      = 2
  min_special      = 2
  min_upper        = 2
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "psql-${local.base_name}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "17"
  delegated_subnet_id           = azurerm_subnet.postgres.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false
  administrator_login           = var.postgres_administrator_login
  administrator_password        = random_password.postgres.result
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  tags                          = local.common_tags

  authentication {
    active_directory_auth_enabled = false
    password_auth_enabled         = true
  }

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "serviceops" {
  name      = "serviceops"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_container_registry" "main" {
  name                          = substr("acr${local.compact_name}", 0, 50)
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  sku                           = "Basic"
  admin_enabled                 = false
  public_network_access_enabled = true
  tags                          = local.common_tags
}

resource "azurerm_user_assigned_identity" "container_pull" {
  name                = "id-acr-pull-${local.base_name}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_role_assignment" "container_pull" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.container_pull.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_eventhub_namespace" "main" {
  name                          = "evhns-${local.base_name}"
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  sku                           = "Standard"
  capacity                      = 1
  auto_inflate_enabled          = false
  local_authentication_enabled  = true
  minimum_tls_version           = "1.2"
  public_network_access_enabled = true
  tags                          = local.common_tags
}

resource "azurerm_eventhub" "topics" {
  for_each          = local.topics
  name              = each.value
  namespace_id      = azurerm_eventhub_namespace.main.id
  partition_count   = 1
  message_retention = 1
}

resource "azurerm_eventhub_namespace_authorization_rule" "applications" {
  name                = "applications"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  listen              = true
  send                = true
  manage              = false
}

resource "azurerm_container_app_environment" "main" {
  name                               = "cae-${local.base_name}"
  location                           = azurerm_resource_group.main.location
  resource_group_name                = azurerm_resource_group.main.name
  infrastructure_subnet_id           = azurerm_subnet.container_apps.id
  infrastructure_resource_group_name = "rg-${local.base_name}-aca-managed"
  internal_load_balancer_enabled     = false
  public_network_access              = "Enabled"
  zone_redundancy_enabled            = false
  tags                               = local.common_tags

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}
