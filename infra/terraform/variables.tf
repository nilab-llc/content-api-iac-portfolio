variable "aws_profile" {
  type        = string
  default     = "nilab-readonly"
  description = "SSO profile. Despite the historical profile name, deployment needs the reviewed scoped write permissions."
}

variable "aws_account_id" {
  type        = string
  default     = "364561592630"
  description = "Explicit account guard; must match the authenticated account."
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Specify a 12-digit account ID."
  }
}

variable "name" {
  type    = string
  default = "nilab-content-tf"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,39}$", var.name))
    error_message = "Use 3-40 lowercase letters, digits and hyphens, starting with a letter."
  }
}

variable "memory_mb" {
  type    = number
  default = 128
  validation {
    condition     = contains([128, 256, 512], var.memory_mb)
    error_message = "Choose 128, 256 or 512 MB for this portfolio."
  }
}

variable "log_retention_days" {
  type    = number
  default = 7
  validation {
    condition     = contains([1, 3, 7, 14, 30], var.log_retention_days)
    error_message = "Choose 1, 3, 7, 14 or 30 days."
  }
}

variable "simulate_storage_failure" {
  type        = bool
  default     = false
  description = "Explicit recovery drill. When enabled, article routes return 503; health remains live."
}
