variable "name_prefix" {
  description = "Lowercase prefix used for Azure resource names."
  type        = string
  default     = "serviceops"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.name_prefix))
    error_message = "name_prefix must be 3-20 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "environment" {
  description = "Short environment label used in names and tags."
  type        = string
  default     = "demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,9}$", var.environment))
    error_message = "environment must be 2-10 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "location" {
  description = "Azure region for all workload resources."
  type        = string
  default     = "westeurope"
}

variable "image_tag" {
  description = "Immutable tag already built in the deployment's Azure Container Registry."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid OCI image tag."
  }
}

variable "postgres_administrator_login" {
  description = "Administrator login for PostgreSQL Flexible Server."
  type        = string
  default     = "serviceopsadmin"
}

variable "operator_username" {
  description = "Bootstrap username for the cloud operator account."
  type        = string
  default     = "operator"
}

variable "viewer_username" {
  description = "Bootstrap username for the cloud read-only account."
  type        = string
  default     = "viewer"
}

variable "otel_exporter_otlp_endpoint" {
  description = "Optional HTTPS OTLP/HTTP endpoint for an externally operated telemetry backend. Null keeps the SDK disabled."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.otel_exporter_otlp_endpoint == null || can(regex("^https://[^[:space:]]+$", var.otel_exporter_otlp_endpoint))
    error_message = "otel_exporter_otlp_endpoint must be null or an HTTPS URL."
  }
}

variable "otel_exporter_otlp_headers" {
  description = "Optional comma-separated OTLP exporter authorization headers stored as Container Apps secrets."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true

  validation {
    condition     = var.otel_exporter_otlp_headers == null || length(trimspace(var.otel_exporter_otlp_headers)) > 0
    error_message = "otel_exporter_otlp_headers must be null or a non-empty header string."
  }
}

variable "otel_traces_sampler_arg" {
  description = "Trace sampling ratio used when an external OTLP endpoint is configured."
  type        = number
  default     = 0.1

  validation {
    condition     = var.otel_traces_sampler_arg > 0 && var.otel_traces_sampler_arg <= 1
    error_message = "otel_traces_sampler_arg must be greater than 0 and no greater than 1."
  }
}

variable "tags" {
  description = "Additional tags merged onto workload resources."
  type        = map(string)
  default     = {}
}
