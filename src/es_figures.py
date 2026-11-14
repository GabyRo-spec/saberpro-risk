"""Regenerate the report figures with Spanish labels (writes to reports/figures_es; JSON/model outputs go to tmp dirs)."""
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = {
 "02_eda.py": {
  'ax.set_xlabel("Mean of the 5 module scores"); ax.set_ylabel("Students")': 'ax.set_xlabel("Promedio de los 5 módulos"); ax.set_ylabel("Estudiantes")',
  '"Derived average score and risk threshold"': '"Promedio derivado y umbral de riesgo"',
  '["Quant.", "Written", "Crit.\\nreading", "English", "Citizen."]': '["Cuant.", "Escrita", "Lect.\\ncrítica", "Inglés", "Ciudad."]',
  '"Records (raw file)"': '"Registros (archivo crudo)"', 'label="score = 0"': 'label="puntaje = 0"', 'label="missing"': 'label="faltante"',
  '"Invalid module scores in the raw file"': '"Puntajes de módulo inválidos en el archivo crudo"',
  '"Car"': '"Automóvil"', '"Washer"': '"Lavadora"', '"Computer"': '"Computador"', '"Work hours"': '"Horas trabajo"', '"Stratum"': '"Estrato"',
  '"Internet"': '"Internet"', '"Mother educ."': '"Educ. madre"', '"Father educ."': '"Educ. padre"', '"Tuition"': '"Matrícula"',
  '"% missing (clean sample)"': '"% faltante (muestra limpia)"', '"Missing values in predictors"': '"Valores faltantes en predictores"',
  'ax.set_ylabel("Score"); ax.set_title("Module scores, IQR outliers (kept)")': 'ax.set_ylabel("Puntaje"); ax.set_title("Puntajes por módulo, atípicos IQR (conservados)")',
  'nm = ["Quant.", "Written", "Crit. r.", "English", "Citizen.", "Mean"]': 'nm = ["Cuant.", "Escrita", "Lect. c.", "Inglés", "Ciudad.", "Prom."]',
  '"Pearson correlation between modules"': '"Correlación de Pearson entre módulos"',
  '"Mode": (df.ESTU_METODO': '"Modalidad": (df.ESTU_METODO', '"Work hours/wk": (': '"Horas trabajo/sem": (',
  '"PRESENCIAL": "Onsite"': '"PRESENCIAL": "Presencial"', '"DISTANCIA": "Distance"': '"DISTANCIA": "Distancia"',
  '"Si": "Yes", "No": "No"': '"Si": "Sí", "No": "No"',
  '"% at risk"': '"% en riesgo"', '"Risk rate by group (dashed = overall 25%; bars = 95% CI)"': '"Tasa de riesgo por grupo (línea = 25% global; barras = IC 95%)"',
  '"Civil engineering"': '"Ing. civil"',
  '"Risk rate, 10 largest fields of study"': '"Tasa de riesgo, 10 núcleos más grandes"',
  'Civil engineering': 'Ing. civil', 'Electronic/telecom eng.': 'Ing. electrónica/telecom.', '"Law"': '"Derecho"',
  'Systems engineering': 'Ing. de sistemas', 'Industrial engineering': 'Ing. industrial', 'Public accounting': 'Contaduría pública',
  'Environmental eng.': 'Ing. ambiental', 'Business administration': 'Administración', '"Education"': '"Educación"', '"Psychology"': '"Psicología"',
 },
 "03_mining.py": {
  '"PCA view of clusters"': '"Clústeres en PCA"', '"Risk by cluster"': '"Riesgo por clúster"', '"% at risk"': '"% en riesgo"',
  '"Choosing k for K-Means"': '"Elección de k en K-Means"', '"Silhouette"': '"Silueta"',
 },
}
for name, rep in R.items():
    s = (HERE / name).read_text()
    for a, b in rep.items():
        if a not in s: print("WARN not found in", name, ":", a[:50])
        s = s.replace(a, b)
    s = s.replace('ROOT / "reports/figures"', 'ROOT / "reports/figures_es"')
    s = re.sub(r'ROOT / "reports/(?!figures_es)', 'ROOT / "reports_tmp/', s)
    s = s.replace('ROOT / "models', 'ROOT / "models_tmp').replace('ROOT / "data/processed/test_predictions.csv"', 'ROOT / "reports_tmp/tp.csv"')
    s = s.replace('ROOT / "api/model"', 'ROOT / "reports_tmp/apimodel"').replace('(ROOT / "api/model")', '(ROOT / "reports_tmp/apimodel")')
    (HERE / ("_es_" + name)).write_text(s)
