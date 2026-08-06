mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      client_id       = "00000000-0000-0000-0000-000000000001"
      object_id       = "00000000-0000-0000-0000-000000000002"
      subscription_id = "00000000-0000-0000-0000-000000000003"
      tenant_id       = "00000000-0000-0000-0000-000000000004"
    }
  }
}

run "demo_topology" {
  command = plan

  variables {
    image_tag = "0123456789abcdef"
  }

  assert {
    condition     = azurerm_postgresql_flexible_server.main.public_network_access_enabled == false
    error_message = "PostgreSQL must not expose a public network endpoint."
  }

  assert {
    condition     = length(azurerm_eventhub.topics) == 3
    error_message = "All three versioned Kafka topics must be represented by Event Hubs."
  }

  assert {
    condition     = azurerm_container_app.backend.ingress[0].external_enabled == false
    error_message = "The backend ingress must remain internal to the Container Apps environment."
  }

  assert {
    condition     = azurerm_container_app.frontend.ingress[0].external_enabled == true
    error_message = "The operator frontend must be the only public application ingress."
  }

  assert {
    condition     = azurerm_container_app.ai.ingress[0].external_enabled == false
    error_message = "The RAG and prediction service ingress must remain internal."
  }

  assert {
    condition     = contains([for env in azurerm_container_app.frontend.template[0].container[0].env : env.name], "AI_HOST")
    error_message = "The frontend proxy must receive the internal AI service hostname."
  }

  assert {
    condition     = azurerm_container_registry.main.admin_enabled == false
    error_message = "ACR administrator credentials must remain disabled."
  }

  assert {
    condition     = azurerm_container_app.ai.template[0].min_replicas == 1
    error_message = "The Kafka prediction worker must not scale to zero."
  }

  assert {
    condition = one([
      for env in azurerm_container_app.backend.template[0].container[0].env : env.value
      if env.name == "OTEL_SDK_DISABLED"
    ]) == "true"
    error_message = "Telemetry export must be disabled unless an external OTLP endpoint is explicitly configured."
  }
}

run "external_telemetry_export" {
  command = plan

  variables {
    image_tag                   = "0123456789abcdef"
    otel_exporter_otlp_endpoint = "https://telemetry.example.com/otlp"
    otel_exporter_otlp_headers  = "Authorization=Bearer example-test-token"
    otel_traces_sampler_arg     = 0.25
  }

  assert {
    condition = one([
      for env in azurerm_container_app.backend.template[0].container[0].env : env.value
      if env.name == "OTEL_SDK_DISABLED"
    ]) == "false"
    error_message = "Providing an OTLP endpoint must enable backend telemetry export."
  }

  assert {
    condition = contains(
      [for env in azurerm_container_app.ai.template[0].container[0].env : env.name],
      "OTEL_EXPORTER_OTLP_HEADERS",
    )
    error_message = "Optional OTLP authorization headers must be injected through a Container Apps secret."
  }
}
