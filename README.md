# Riesgo de bajo desempeño en Saber Pro — Proyecto integrador (USTA Tunja)

Materias: Minería de Datos, Machine Learning y Cloud Computing. Informe de avance en `reports/` (PDF y Word, en español).

    pip install -r requirements.txt
    ./run_all.sh            # regenera datos limpios, figuras, resultados e informe

Carpetas: `data/` (CSV original y limpio) · `src/` (scripts numerados 01..10) · `api/` (Lambda en Python puro + `model/model.json`) ·
`terraform/` (infraestructura para el plan gratuito de AWS) · `reports/` (resultados JSON, figuras, informe) · `evidencia/` (salidas y capturas del despliegue en AWS).

## AWS (plan gratuito)
Lambda (Function URL) + S3 + CloudWatch Logs + AWS Budgets, todo creado con Terraform. Sin Docker, sin ECR, sin API Gateway, sin VPC.

    cd terraform
    cp terraform.tfvars.example terraform.tfvars   # poner tu correo
    terraform init && terraform plan && terraform apply
    curl <api_url>health
    terraform destroy                              # al terminar

## Estado y evidencia (14 de noviembre de 2026)
Terraform se ejecutó en una cuenta real de AWS (región `us-east-1`) y la API se probó desde internet. La evidencia está en `evidencia/`:

| Archivo | Qué muestra |
|---|---|
| `01_init.txt` | `terraform init` |
| `02_validate.txt` | `terraform validate`: configuración válida |
| `03_plan.txt` | `terraform plan`: 14 recursos por crear |
| `04_apply.txt` | `terraform apply`: 14 recursos creados |
| `05_outputs.txt` | URL de la API y bucket creados |
| `06_health.txt` | respuesta de `GET /health` |
| `07_body.json`, `07_predict.txt` | entrada y respuesta de `POST /predict` |
| `08_demo_navegador.png` | página de prueba abierta desde el navegador |
| `09_consola_lambda.png` | función Lambda en la consola de AWS |

`override.tf` solo activa `force_destroy` en el bucket para que `terraform destroy` pueda borrarlo aunque tenga versiones.

Completado: cruce de acreditación oficial del SNIES (`scraping_snies.ipynb` y `saber_pro_con_acreditacion.csv`) como análisis descriptivo en la Sección IV-G.
