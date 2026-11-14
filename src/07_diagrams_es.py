"""Step 07 (v2, Spanish) - system and AWS free-plan architecture diagrams."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
ROOT = Path(__file__).resolve().parents[1]; FIG = ROOT / "reports/figures_es"; FIG.mkdir(parents=True, exist_ok=True)
NAVY, RED, GREY, GREEN, GOLD = "#1f4e79", "#c0504d", "#7f7f7f", "#4f9d69", "#e0a030"
def box(ax, x, y, w, h, t, fc="#eaf1f8", ec=NAVY, fs=6, dashed=False, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015", fc=fc, ec=ec, lw=.9, ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.15)
def arrow(ax, p, q, color=NAVY, dashed=False):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6, lw=.9, color=color, ls="--" if dashed else "-"))
# ---- system (CRISP-DM style flow)
fig, ax = plt.subplots(figsize=(3.4, 3.9)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
box(ax, .05, .90, .42, .08, "Archivo ICFES Saber Pro\n4.645 filas, 57 columnas", fc="#f2f2f2", ec=GREY)
box(ax, .55, .90, .40, .08, "Acreditación SNIES\n(opcional, scraping)", fc="#f2f2f2", ec=GREY, dashed=True)
box(ax, .05, .74, .90, .09, "Preparación de datos\nduplicados | puntajes inválidos | nulos | atípicos | etiqueta", bold=True)
box(ax, .05, .56, .42, .13, "Minería de datos\nEDA, K-Means, jerárquico,\nDBSCAN, Apriori / FP-Growth", fc="#e6f2ea", ec=GREEN)
box(ax, .53, .56, .42, .13, "Machine Learning\nRL, KNN, SVM, árboles,\nensambles, búsqueda de hiperparám.", fc="#fbeee6", ec=GOLD)
box(ax, .05, .40, .90, .09, "Modelo elegido (regresión logística) en un archivo JSON\n+ resultados, figuras, reglas y perfiles", bold=True)
box(ax, .05, .17, .90, .15, "Nube en AWS (capa gratuita) con Terraform\nLambda (Function URL) lee el modelo desde S3\nalerta de presupuesto y logs", fc="#f6e9e9", ec=RED)
box(ax, .05, .02, .90, .08, "Equipo del programa: riesgo del estudiante + factores principales", fc="#f2f2f2", ec=GREY)
arrow(ax, (.26, .90), (.26, .83)); arrow(ax, (.75, .90), (.75, .83), color=GREY, dashed=True)
arrow(ax, (.26, .74), (.26, .69)); arrow(ax, (.74, .74), (.74, .69)); arrow(ax, (.26, .56), (.26, .49)); arrow(ax, (.74, .56), (.74, .49))
arrow(ax, (.50, .40), (.50, .32)); arrow(ax, (.50, .17), (.50, .10))
fig.tight_layout(pad=.2); fig.savefig(FIG / "fig_system.png", dpi=220); plt.close()
# ---- AWS free-plan architecture
fig, ax = plt.subplots(figsize=(3.4, 3.8)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
ax.add_patch(FancyBboxPatch((.02, .22), .96, .52, boxstyle="round,pad=0.005,rounding_size=0.02", fc="none", ec=GREY, lw=.8, ls="--"))
ax.text(.04, .235, "Cuenta AWS (plan gratuito), us-east-1, sin VPC y sin NAT gateway", fontsize=5, color=GREY, ha="left", va="bottom")
box(ax, .30, .88, .40, .09, "Usuario / analista\n(navegador, curl)", fc="#f2f2f2", ec=GREY)
box(ax, .15, .58, .70, .10, "Lambda Function URL (HTTPS)\nGET / | GET /health | POST /predict", fs=5.8)
box(ax, .15, .40, .70, .11, "AWS Lambda (FaaS), Python 3.12, 512 MB\nregresión logística en Python puro", fs=5.8, fc="#fbeee6", ec=GOLD)
box(ax, .08, .27, .38, .08, "S3 privado\nmodels/model.json (versionado)", fs=5.3)
box(ax, .54, .27, .38, .08, "CloudWatch Logs\n(14 días)", fs=5.5)
arrow(ax, (.50, .88), (.50, .68)); arrow(ax, (.50, .58), (.50, .51))
arrow(ax, (.32, .40), (.27, .35)); arrow(ax, (.68, .40), (.73, .35))
ax.text(.20, .375, "lee el modelo", fontsize=4.8, color=GREY, ha="right"); ax.text(.80, .375, "escribe logs", fontsize=4.8, color=GREY, ha="left")
box(ax, .03, .08, .44, .09, "Terraform crea todo lo anterior\n(IaC, un solo terraform apply)", fc="#e6f2ea", ec=GREEN, fs=5.4)
box(ax, .52, .08, .21, .09, "Rol IAM\n(solo esta Lambda)", fs=5)
box(ax, .76, .08, .21, .09, "AWS Budgets\ncorreo al 80%", fs=5)
ax.text(.03, .02, "Control y salvaguardas", fontsize=5.2, color=GREY)
fig.tight_layout(pad=.2); fig.savefig(FIG / "fig_cloud.png", dpi=220); plt.close()
print("ok")
