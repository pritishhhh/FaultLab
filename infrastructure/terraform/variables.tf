variable "aws_region" {
  type    = string
  default = "us-east-1"
}
variable "environment" {
  type    = string
  default = "demo"
}
variable "vpc_cidr" {
  type    = string
  default = "10.84.0.0/16"
}
variable "certificate_arn" {
  type        = string
  description = "Validated ACM certificate for the public HTTPS endpoint"
}
variable "domain_name" {
  type        = string
  description = "DNS name covered by the ACM certificate and pointed at the ALB"
}
variable "allowed_cidrs" {
  type        = list(string)
  description = "Trusted client CIDR ranges allowed to reach the HTTPS demo ALB"
  validation {
    condition     = length(var.allowed_cidrs) > 0
    error_message = "At least one trusted CIDR is required."
  }
}
variable "internal_token_secret_arn" {
  type        = string
  description = "Existing Secrets Manager secret containing the internal fault token"
}
variable "image_tag" {
  type    = string
  default = "latest"
}
variable "start_services" {
  type    = bool
  default = false
}
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}
variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}
