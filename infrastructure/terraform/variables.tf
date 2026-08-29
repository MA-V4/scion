variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "gateway_replicas" {
  description = "Number of gateway pod replicas"
  type        = number
  default     = 3
}
