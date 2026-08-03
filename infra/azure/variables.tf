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

variable "tags" {
  description = "Additional tags merged onto workload resources."
  type        = map(string)
  default     = {}
}
