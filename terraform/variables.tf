variable "aws_region" {
  description = "Region. us-east-1 es la que se usa para estimar costos."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  type    = string
  default = "saberpro-risk"
}

variable "lambda_memory_mb" {
  description = "Memoria de la Lambda. 512 MB sobra para una regresion logistica en Python puro."
  type        = number
  default     = 512
}

variable "max_concurrency" {
  description = "Tope de ejecuciones simultaneas (-1 = sin tope). En cuentas nuevas el limite total puede ser bajo y reservar concurrencia puede fallar; subirlo solo si la cuenta lo permite."
  type        = number
  default     = -1
}

variable "monthly_budget_usd" {
  description = "Presupuesto mensual para la alerta de costos."
  type        = number
  default     = 5
}

variable "alert_email" {
  description = "Correo que recibe las alertas del presupuesto."
  type        = string
}
