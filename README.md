# Riesgo de bajo desempeño en Saber Pro — Proyecto integrador (USTA Tunja)

Materias: Minería de Datos, Machine Learning y Cloud Computing. Informe de avance en `reports/` (PDF y Word, en español).

    pip install -r requirements.txt
    ./run_all.sh            # regenera datos limpios, figuras, resultados e informe

Carpetas: `data/` (CSV original y limpio) · `src/` (scripts numerados 01..10) · `api/` (Lambda en Python puro + `model/model.json`) ·
`terraform/` (infraestructura para el plan gratuito de AWS) · `reports/` (resultados JSON, figuras, informe).

## AWS (plan gratuito)
Lambda (Function URL) + S3 + CloudWatch Logs + AWS Budgets, todo creado con Terraform. Sin Docker, sin ECR, sin API Gateway, sin VPC.

    cd terraform
    cp terraform.tfvars.example terraform.tfvars   # poner tu correo
    terraform init && terraform plan && terraform apply
    curl <api_url>health
    terraform destroy                              # al terminar

Estado: el HCL se leyó correctamente, pero `terraform validate/plan/apply` NO se han ejecutado, ni se ha probado la URL en AWS.
`src/scrape_snies.py` tampoco se ha ejecutado ni validado contra el sitio.
