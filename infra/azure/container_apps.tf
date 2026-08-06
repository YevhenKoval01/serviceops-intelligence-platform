locals {
  eventhubs_bootstrap_server = "${azurerm_eventhub_namespace.main.name}.servicebus.windows.net:9093"
  eventhubs_jaas_config = format(
    "org.apache.kafka.common.security.plain.PlainLoginModule required username=\"$ConnectionString\" password=\"%s\";",
    azurerm_eventhub_namespace_authorization_rule.applications.primary_connection_string,
  )

  telemetry_environment = var.otel_exporter_otlp_endpoint == null ? tomap({
    OTEL_SDK_DISABLED = "true"
    }) : tomap({
    OTEL_SDK_DISABLED           = "false"
    OTEL_EXPORTER_OTLP_ENDPOINT = var.otel_exporter_otlp_endpoint
    OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"
    OTEL_TRACES_EXPORTER        = "otlp"
    OTEL_METRICS_EXPORTER       = "otlp"
    OTEL_LOGS_EXPORTER          = "otlp"
    OTEL_PROPAGATORS            = "tracecontext,baggage"
    OTEL_TRACES_SAMPLER         = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG     = tostring(var.otel_traces_sampler_arg)
    OTEL_RESOURCE_ATTRIBUTES    = "deployment.environment.name=${var.environment},cloud.provider=azure,service.namespace=serviceops"
  })
  telemetry_secret_environment = var.otel_exporter_otlp_headers == null ? {} : {
    OTEL_EXPORTER_OTLP_HEADERS = "otel-exporter-headers"
  }
  telemetry_secrets = var.otel_exporter_otlp_headers == null ? {} : {
    otel-exporter-headers = var.otel_exporter_otlp_headers
  }

  backend_environment = merge({
    SPRING_DATASOURCE_URL                                = "jdbc:postgresql://${azurerm_postgresql_flexible_server.main.fqdn}:5432/serviceops?sslmode=require"
    SPRING_DATASOURCE_USERNAME                           = var.postgres_administrator_login
    SPRING_KAFKA_BOOTSTRAP_SERVERS                       = local.eventhubs_bootstrap_server
    SPRING_KAFKA_PROPERTIES_SECURITY_PROTOCOL            = "SASL_SSL"
    SPRING_KAFKA_PROPERTIES_SASL_MECHANISM               = "PLAIN"
    SPRING_KAFKA_PROPERTIES_METADATA_MAX_AGE_MS          = "180000"
    SPRING_KAFKA_PROPERTIES_CONNECTIONS_MAX_IDLE_MS      = "180000"
    SPRING_KAFKA_PRODUCER_PROPERTIES_REQUEST_TIMEOUT_MS  = "60000"
    SPRING_KAFKA_PRODUCER_PROPERTIES_DELIVERY_TIMEOUT_MS = "120000"
    SPRING_KAFKA_PRODUCER_PROPERTIES_MAX_REQUEST_SIZE    = "1000000"
    SERVICEOPS_TOPICS_MANAGE                             = "false"
    SERVICEOPS_OUTBOX_SEND_TIMEOUT_MS                    = "70000"
    SERVICEOPS_AUTH_ISSUER                               = "serviceops-${var.environment}"
    SERVICEOPS_AUTH_AUDIENCE                             = "serviceops-api"
    SERVICEOPS_AUTH_TOKEN_TTL                            = "15m"
    SERVICEOPS_AUTH_BOOTSTRAP_ENABLED                    = "true"
    SERVICEOPS_AUTH_OPERATOR_USERNAME                    = var.operator_username
    SERVICEOPS_AUTH_VIEWER_USERNAME                      = var.viewer_username
    SERVICEOPS_KAFKA_HEALTH_TIMEOUT                      = "10s"
    OTEL_SERVICE_NAME                                    = "serviceops-backend"
  }, local.telemetry_environment)
  backend_secret_environment = merge({
    SPRING_DATASOURCE_PASSWORD               = "postgres-password"
    SPRING_KAFKA_PROPERTIES_SASL_JAAS_CONFIG = "eventhubs-jaas"
    SERVICEOPS_AUTH_JWT_SECRET               = "jwt-secret"
    SERVICEOPS_AUTH_OPERATOR_PASSWORD        = "operator-password"
    SERVICEOPS_AUTH_VIEWER_PASSWORD          = "viewer-password"
  }, local.telemetry_secret_environment)
  backend_secrets = merge({
    postgres-password = random_password.postgres.result
    eventhubs-jaas    = local.eventhubs_jaas_config
    jwt-secret        = random_password.jwt.result
    operator-password = random_password.operator.result
    viewer-password   = random_password.viewer.result
  }, local.telemetry_secrets)

  ai_environment = merge({
    KAFKA_BOOTSTRAP_SERVERS       = local.eventhubs_bootstrap_server
    KAFKA_ENABLED                 = "true"
    KAFKA_PROFILE                 = "azure-event-hubs"
    KAFKA_SECURITY_PROTOCOL       = "SASL_SSL"
    KAFKA_SASL_MECHANISM          = "PLAIN"
    KAFKA_SASL_USERNAME           = "$ConnectionString"
    KAFKA_PRODUCE_TIMEOUT_SECONDS = "70"
    MODEL_PATH                    = "/tmp/serviceops-baseline.joblib"
    SERVICEOPS_AUTH_ISSUER        = "serviceops-${var.environment}"
    SERVICEOPS_AUTH_AUDIENCE      = "serviceops-api"
    OTEL_SERVICE_NAME             = "serviceops-ai-service"
  }, local.telemetry_environment)
  ai_secret_environment = merge({
    KAFKA_SASL_PASSWORD        = "eventhubs-connection"
    SERVICEOPS_AUTH_JWT_SECRET = "jwt-secret"
  }, local.telemetry_secret_environment)
  ai_secrets = merge({
    eventhubs-connection = azurerm_eventhub_namespace_authorization_rule.applications.primary_connection_string
    jwt-secret           = random_password.jwt.result
  }, local.telemetry_secrets)
}

resource "azurerm_container_app" "backend" {
  name                         = "backend-${local.base_name}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_pull.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.container_pull.id
  }

  dynamic "secret" {
    for_each = local.backend_secrets
    content {
      name  = secret.key
      value = secret.value
    }
  }

  template {
    min_replicas                     = 1
    max_replicas                     = 1
    termination_grace_period_seconds = 30

    container {
      name   = "backend"
      image  = "${azurerm_container_registry.main.login_server}/serviceops-backend:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = local.backend_environment
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.backend_secret_environment
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      startup_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/actuator/health/readiness"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/actuator/health/readiness"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 6
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/actuator/health/liveness"
        initial_delay           = 30
        interval_seconds        = 20
        timeout                 = 5
        failure_count_threshold = 3
      }
    }
  }

  ingress {
    external_enabled           = false
    allow_insecure_connections = false
    target_port                = 8080
    transport                  = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_eventhub.topics,
    azurerm_postgresql_flexible_server_database.serviceops,
    azurerm_role_assignment.container_pull,
  ]
}

resource "azurerm_container_app" "ai" {
  name                         = "ai-${local.base_name}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_pull.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.container_pull.id
  }

  dynamic "secret" {
    for_each = local.ai_secrets
    content {
      name  = secret.key
      value = secret.value
    }
  }

  template {
    min_replicas                     = 1
    max_replicas                     = 1
    termination_grace_period_seconds = 30

    container {
      name   = "ai-service"
      image  = "${azurerm_container_registry.main.login_server}/serviceops-ai:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = local.ai_environment
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.ai_secret_environment
        content {
          name        = env.key
          secret_name = env.value
        }
      }

      startup_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 30
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 6
      }
    }
  }

  ingress {
    external_enabled           = false
    allow_insecure_connections = false
    target_port                = 8000
    transport                  = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_eventhub.topics,
    azurerm_role_assignment.container_pull,
  ]
}

resource "azurerm_container_app" "frontend" {
  name                         = "web-${local.base_name}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_pull.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.container_pull.id
  }

  template {
    min_replicas = 0
    max_replicas = 2

    container {
      name   = "frontend"
      image  = "${azurerm_container_registry.main.login_server}/serviceops-frontend:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "BACKEND_SCHEME"
        value = "https"
      }

      env {
        name  = "BACKEND_HOST"
        value = azurerm_container_app.backend.latest_revision_fqdn
      }

      env {
        name  = "BACKEND_PORT"
        value = "443"
      }

      env {
        name  = "AI_SCHEME"
        value = "https"
      }

      env {
        name  = "AI_HOST"
        value = azurerm_container_app.ai.latest_revision_fqdn
      }

      env {
        name  = "AI_PORT"
        value = "443"
      }

      startup_probe {
        transport               = "HTTP"
        port                    = 80
        path                    = "/health"
        interval_seconds        = 5
        timeout                 = 3
        failure_count_threshold = 12
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 80
        path                    = "/health"
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 80
        path                    = "/health"
        initial_delay           = 10
        interval_seconds        = 20
        timeout                 = 3
        failure_count_threshold = 3
      }
    }
  }

  ingress {
    external_enabled           = true
    allow_insecure_connections = false
    target_port                = 80
    transport                  = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_role_assignment.container_pull]
}
