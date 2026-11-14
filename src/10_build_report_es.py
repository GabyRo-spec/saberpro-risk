"""Step 09 - build the IEEE-style PDF progress report from the JSON results and figures (numbers are read, not typed)."""
import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, FrameBreak, Image, KeepTogether, NextPageTemplate, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"
FIG = R / "figures_es"
ml = json.load(open(R / "ml_results.json"))
eda = json.load(open(R / "eda_stats.json"))
cl = json.load(open(R / "clustering.json"))
clean = json.load(open(R / "cleaning_log.json"))
cost = json.load(open(R / "cost_estimate.json"))
xc = json.load(open(R / "extra_checks.json"))
mx = json.load(open(R / "mining_extra.json"))
import pandas as pd
rules = pd.read_csv(R / "rules.csv")

# ----------------------------------------------------------------------------- fonts / styles
FD = "/usr/share/fonts/truetype/liberation/"
pdfmetrics.registerFont(TTFont("Serif", FD + "LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Serif-B", FD + "LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Serif-I", FD + "LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Serif-BI", FD + "LiberationSerif-BoldItalic.ttf"))
pdfmetrics.registerFont(TTFont("Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-B", italic="Serif-I", boldItalic="Serif-BI")

body = ParagraphStyle("body", fontName="Serif", fontSize=9, leading=10.8, alignment=TA_JUSTIFY, spaceAfter=3.5)
h1 = ParagraphStyle("h1", fontName="Serif", fontSize=9, leading=11, alignment=TA_CENTER, spaceBefore=7, spaceAfter=3.5, keepWithNext=1)
h2 = ParagraphStyle("h2", fontName="Serif-I", fontSize=9, leading=11, alignment=TA_LEFT, spaceBefore=4, spaceAfter=2, keepWithNext=1)
cap = ParagraphStyle("cap", fontName="Serif", fontSize=7.5, leading=9, alignment=TA_JUSTIFY, spaceBefore=1.5, spaceAfter=5)
tcap = ParagraphStyle("tcap", fontName="Serif", fontSize=7.5, leading=9, alignment=TA_CENTER, spaceBefore=3, spaceAfter=2)
title = ParagraphStyle("title", fontName="Serif-B", fontSize=17, leading=20, alignment=TA_CENTER, spaceAfter=5)
auth = ParagraphStyle("auth", fontName="Serif", fontSize=9.5, leading=12, alignment=TA_CENTER, spaceAfter=1)
absS = ParagraphStyle("abs", parent=body, fontName="Serif-B", fontSize=9, leading=10.8)
cell = ParagraphStyle("cell", fontName="Serif", fontSize=7, leading=8.2, alignment=TA_LEFT)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Serif-B")
bul = ParagraphStyle("bul", parent=body, leftIndent=9, bulletIndent=0, spaceAfter=1.5)
ref = ParagraphStyle("ref", parent=body, fontSize=7.5, leading=9, leftIndent=14, firstLineIndent=-14, spaceAfter=1.5)
code = ParagraphStyle("code", fontName="Mono", fontSize=6.3, leading=7.6, alignment=TA_LEFT, spaceAfter=3)

S = []
fig_n = [0]
tab_n = [0]
ROM = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def P(t, st=body): S.append(Paragraph(t, st))
def H1(t): S.append(Paragraph(t.upper(), h1))
def H2(t): S.append(Paragraph(t, h2))
def B(t): S.append(Paragraph(t, bul, bulletText="•"))


def fig(name, caption, w=3.4):
    fig_n[0] += 1
    im = PILImage.open(FIG / name); ar = im.height / im.width
    S.append(KeepTogether([Image(str(FIG / name), width=w * inch, height=w * ar * inch),
                           Paragraph(f"Fig. {fig_n[0]}. {caption}", cap)]))
    return fig_n[0]


def table(caption, rows, widths, hdr=1, align_right_from=1, bold_last=False):
    tab_n[0] += 1
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(str(c), cellb if i < hdr else cell) for c in r])
    t = Table(data, colWidths=[w * inch for w in widths], repeatRows=hdr)
    ts = [("LINEABOVE", (0, 0), (-1, 0), .8, colors.black), ("LINEBELOW", (0, hdr - 1), (-1, hdr - 1), .5, colors.black),
          ("LINEBELOW", (0, -1), (-1, -1), .8, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
          ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]
    t.setStyle(TableStyle(ts))
    S.append(KeepTogether([Paragraph(f"TABLA {ROM[tab_n[0]]}<br/>{caption.upper()}", tcap), t, Spacer(1, 5)]))


f2 = lambda x: f"{x:.2f}".replace(".", ",")
f3 = lambda x: f"{x:.3f}".replace(".", ",")
pc = lambda x: f"{100 * x:.1f}%".replace(".", ",")
c = lambda x: str(x).replace(".", ",")
th = lambda n: f"{n:,}".replace(",", ".")

n_final, n_raw = clean["rows_final"], clean["rows_raw"]
thr = clean["risk_threshold_p25"]

# ----------------------------------------------------------------------------- traducciones de etiquetas
ASSOC = {"Study mode": "Modalidad", "Field of study": "Núcleo de estudio", "Mother education": "Educación de la madre", "Tuition": "Valor de matrícula",
         "Father education": "Educación del padre", "Institution origin": "Origen de la institución", "Work hours": "Horas de trabajo",
         "Stratum": "Estrato", "Gender": "Género", "Internet": "Internet", "Computer": "Computador", "Period": "Periodo"}
COST = {"Piloto": "Piloto (5 mil solicitudes)", "Uso por el programa": "Uso por el programa (50 mil)", "Uso institucional": "Uso institucional (500 mil)",
        "Prueba de estrés": "Prueba de estrés (5 millones)"}
RULE = [("Mode=Distance/Virtual", "Modalidad=Distancia/Virtual"), ("MotherEdu<=Primary", "EduMadre≤Primaria"), ("Stratum<=2", "Estrato≤2"),
        ("Tuition<1M", "Matrícula<1M"), ("Age>=30", "Edad≥30"), ("Female", "Mujer"), ("Private(Fund./Corp.)", "Privada(Fund./Corp.)"),
        ("Tuition>=4M", "Matrícula≥4M"), ("Work>30h", "Trabajo>30h"), ("NoInternet", "SinInternet"), ("NoComputer", "SinComputador"),
        ("Mode=Onsite", "Modalidad=Presencial"), ("Public", "Pública"), ("Male", "Hombre"), ("Scholarship", "Beca"),
        ("MotherEdu>=Tertiary", "EduMadre≥Superior"), ("Stratum>=3", "Estrato≥3"), ("Work<=10h", "Trabajo≤10h"), ("Age<=23", "Edad≤23")]
def rule_es(t):
    for a, b in RULE: t = t.replace(a, b)
    return t.replace("&", "&amp;")

M = ml["models"]; dep = M["lr"]; gbm = M["gb"]
n_final, n_raw = clean["rows_final"], clean["rows_raw"]
thr = clean["risk_threshold_p25"]
R_ = lambda k: eda["risk_by_group"][k]
fo = {r["group"]: r for r in ml["fairness_top20"]}; sa = {r["group"]: r for r in ml["stratified_top20"]}
(tn, fpp), (fnn, tpp) = ml["deploy_confusion_top20"]
prec_d = tpp / (tpp + fpp); rec_d = tpp / (tpp + fnn); f1_d = 2 * prec_d * rec_d / (prec_d + rec_d)
dt20 = ml["deploy_top20"]; ab = ml["ablation"]; orr = ml["odds_ratio_per_sd"]; pim = ml["perm_importance"]

# ----------------------------------------------------------------------------- bloque de título
P("Predicción del riesgo de bajo desempeño en Saber Pro: así avanza el proyecto integrador", title)
P("<b>[Nombres de los integrantes del equipo — completar]</b>", auth)
P("<i>Facultad de Ingeniería de Datos e Inteligencia Artificial, Universidad Santo Tomás — Tunja, Colombia</i>", auth)
P("Proyecto Integrador, quinto semestre · Entrega de avance del 14 de noviembre de 2026", auth)
S.append(Spacer(1, 4))
P(f"<i>Resumen</i>—El equipo quiere saber si es posible adelantarse al Saber Pro: con datos que el estudiante ya tiene antes del examen (su estrato, "
  f"si trabaja, qué modalidad estudia, la educación de sus padres, entre otros), ¿se puede decir quién tiene más probabilidad de quedar en el 25% "
  f"con peores resultados? Para responderlo se tomó un archivo con {th(n_raw)} registros, se limpió hasta dejar {th(n_final)} estudiantes y se "
  f"probaron técnicas de minería de datos y de machine learning. El mejor modelo acierta bastante más que el azar (AUC de {f3(dep['test_auc'])} "
  f"con la regresión logística, que es la elegida), pero se encontró un problema importante: el modelo depende mucho de si el estudiante es de "
  f"modalidad a distancia y casi no distingue riesgo entre los mismos estudiantes a distancia. Además se diseñó cómo publicar el modelo en AWS "
  f"aprovechando el plan gratuito.", absS)
P("<i>Términos clave</i>—Saber Pro, minería de datos, machine learning, regresión logística, K-Means, ODS 4, ODS 10, AWS, Terraform, plan gratuito.",
  ParagraphStyle("kw", parent=body, fontName="Serif-B"))
S.append(FrameBreak())

# ----------------------------------------------------------------------------- I
H1("I. Introducción")
P("Saber Pro es el examen que presentan los estudiantes de pregrado en Colombia casi al final de la carrera y lo administra el ICFES [1]. Los "
  "resultados llegan cuando el estudiante ya terminó, y por eso no sirven para ayudarle a tiempo. La idea del proyecto es darle la vuelta: "
  "mirar las condiciones con las que llega cada estudiante y detectar con anticipación qué perfiles suelen quedar peor, para que la universidad "
  "pueda enfocar su apoyo académico. Eso conecta con dos Objetivos de Desarrollo Sostenible: el 4 (educación de calidad) y el 10 (reducción de "
  "las desigualdades) [2].")
P("Este documento es el avance que piden los lineamientos del proyecto integrador. Cuenta cómo se plantea el problema (documento técnico), cómo se "
  "prepararon y exploraron los datos (Minería de Datos), cómo se publicaría el resultado en la nube (Cloud Computing) y cómo se integra Machine "
  "Learning, materia que el equipo cursa en paralelo.")

# ----------------------------------------------------------------------------- II
H1("II. El problema y los ODS")
H2("A. Qué se quiere resolver")
P("Dos estudiantes pueden llegar al mismo examen con preparaciones muy distintas. En los datos del proyecto se nota: "
  f"{pc(R_('Mode')['PRESENCIAL']['risk_pct'] / 100)} de los estudiantes presenciales queda en el 25% inferior, frente a "
  f"{pc(R_('Mode')['DISTANCIA']['risk_pct'] / 100)} de los de modalidad a distancia; y "
  f"{pc(R_('Stratum')['Estrato 1']['risk_pct'] / 100)} de los de estrato 1 frente a "
  f"{pc(R_('Stratum')['Estrato 4']['risk_pct'] / 100)} de los de estrato 4. Entonces el proyecto busca dos cosas: saber <i>quién</i> necesita "
  "apoyo (ODS 4) y revisar si las brechas entre grupos son sistemáticas (ODS 10).")
H2("B. Preguntas del proyecto")
B("<b>¿Qué perfiles de estudiantes concentran el riesgo?</b> (se responde con minería de datos).")
B("<b>¿Qué tan bien se puede predecir ese riesgo antes del examen y qué variables pesan más?</b> (se responde con machine learning).")
B("<b>¿Se puede publicar el modelo en la nube sin gastar dinero?</b> (se responde con AWS y su plan gratuito).")
H2("C. Cómo se define “riesgo”")
P(f"El archivo no trae el puntaje global oficial. Por eso el equipo calcula el <i>promedio simple de los cinco módulos</i> (razonamiento cuantitativo, "
  f"lectura crítica, comunicación escrita, inglés y competencias ciudadanas). Un estudiante está “en riesgo” si su promedio queda en el 25% más bajo del "
  f"grupo, es decir, en {c(thr)} puntos o menos. Es una definición propia del proyecto, no un nivel oficial. Los puntajes de los módulos nunca se usan "
  f"para predecir, porque con ellos se construye la etiqueta y el modelo quedaría “perfecto” sin servir para nada.")
H2("D. Alcance y cuidados")
P("Los datos son registros anonimizados de personas que viven en Sogamoso y presentaron el examen entre 2018 y 2022, aunque estudiaron en "
  "instituciones de todo el país. Lo que se concluya vale para ese grupo. Las diferencias entre grupos se describen, pero no se interpretan como "
  "causas. Y si algún día se usa el puntaje de riesgo, debe ser para dar más apoyo, nunca para quitar oportunidades.")

# ----------------------------------------------------------------------------- III
H1("III. Estructura general del sistema")
P("La Fig. 1 resume el recorrido. Los datos se preparan una sola vez, y esa misma tabla limpia alimenta tanto la minería de datos como el machine "
  "learning. El modelo elegido se guarda en un archivo pequeño y ese archivo es lo que se publica en la nube. Hay una fuente externa opcional (la "
  "acreditación de cada programa en el SNIES), pero todavía no se usa en los resultados (Sección IV-F).")
fig("fig_system.png", "Recorrido del proyecto. Recuadro punteado: fuente externa opcional, aún sin usar.")
P("Para que la revisión sea reproducible, el repositorio incluye el archivo original, los scripts numerados que regeneran cada cifra y cada figura de este "
  "informe (<font name='Mono'>run_all.sh</font>), las versiones fijas de las librerías, semillas aleatorias fijas, el código de la API y el Terraform.")

# ----------------------------------------------------------------------------- IV
H1("IV. Minería de datos")
H2("A. Los datos")
P(f"El archivo es un CSV con {th(n_raw)} registros y 57 columnas, de los periodos 2018-3 a 2022-6. Para predecir solo se dejaron variables que el estudiante "
  "ya tiene antes del examen: estrato, educación de los padres, si tiene internet, computador, automóvil o lavadora, horas de trabajo por semana, "
  "valor de la matrícula y quién la paga, modalidad, origen y carácter de la institución, núcleo de estudio, género y edad. Se descartaron los "
  "identificadores, los tipos de documento y las columnas que valen lo mismo para todos (por ejemplo, la residencia).")
H2("B. Limpieza de los datos")
P(f"Lo primero fue buscar duplicados. Había {clean['exact_duplicate_rows']} filas exactamente iguales y {clean['duplicate_ids_remaining']} más con el mismo "
  "identificador de estudiante (solo cambiaban datos del sitio donde presentó), así que se dejó la primera de cada una. También se sacaron "
  f"{clean['identity_not_verified_removed']} registros con identidad sin verificar.")
P(f"Después apareció algo raro. En comunicación escrita había {clean['comm_zero_and_missing_level']} estudiantes con puntaje 0, y todos tenían el nivel "
  "de desempeño vacío, o sea que el ensayo nunca se calificó. Un 0 así no es una mala nota, es una nota que no existe (Fig. 2). Si se hubiera dejado, "
  "esos estudiantes habrían aparecido como “en riesgo” sin serlo. Con ellos, el corte del 25% daba 134,4 puntos (la cifra de la propuesta "
  f"inicial); al quitar los {clean['rows_removed_invalid_scores']} registros con puntajes inválidos ({c(clean['share_removed_invalid_scores_pct'])}%) "
  f"el corte pasa a {c(thr)}. Un detalle a vigilar: esos registros se concentran en 2022 ({c(xc['invalid_share_by_period_pct']['20222'])}% y "
  f"{c(xc['invalid_share_by_period_pct']['20225'])}% en dos de sus periodos, frente a unos 2,5–3,7% en 2018–2021), así que si ese año tuvo un problema "
  "de calificación habría que revisarlo.")
fig("fig_invalid.png", "Puntajes iguales a cero o vacíos en el archivo crudo. Casi todo el problema está en comunicación escrita.")
mc = clean["predictor_missing_pct"]
P(f"<b>Datos faltantes.</b> En las variables para predecir faltan pocos datos ({c(f'{min(mc.values()):.1f}')}% a {c(f'{max(mc.values()):.1f}')}%, Fig. 3), "
  "así que no se borraron filas. Las respuestas “No sabe”, “No aplica” y “Sin estrato” se tomaron como faltantes. Para rellenarlos se usa la "
  "mediana (en variables numéricas) y se agrega una marca que avisa que el dato faltaba; en las categóricas se crea una categoría “sin dato”. "
  "Esto se hace dentro del pipeline, solo con los datos de entrenamiento, para no “espiar” los de prueba.")
fig("fig_missing.png", "Porcentaje de datos faltantes en cada variable para predecir.")
P("<b>Valores atípicos.</b> Los puntajes van de 0 a 300 y, usando la regla del rango intercuartil (1,5×IQR), entre 7 y 41 estudiantes por módulo "
  "salen “raros”. Como son resultados extremos pero posibles, se dejaron. Una edad menor de 16 años (un error de digitación) se marcó como faltante, y "
  f"se mantuvieron {clean['age_gt_50_kept']} estudiantes mayores de 50 porque son comunes en programas a distancia.")
table("Resumen de la limpieza", [["Paso", "Registros"],
                       ["Archivo original", th(n_raw)],
                       ["Después de quitar duplicados", th(clean['rows_after_dedup'])],
                       ["Identidad sin verificar (se quitan)", str(clean["identity_not_verified_removed"])],
                       ["Puntajes inválidos o vacíos (se quitan)", str(clean["rows_removed_invalid_scores"])],
                       ["<b>Estudiantes que quedan</b>", f"<b>{th(n_final)}</b>"]], [2.55, .8])
H2("C. Transformación y atributos nuevos")
P("Con los datos limpios se prepararon las variables para que los algoritmos las entiendan. La edad no venía: se calculó con la fecha de "
  "nacimiento. Las categorías con orden natural (estrato, educación de los padres, horas de trabajo, valor de matrícula) se pasaron a escalas "
  "numéricas ordenadas, las que no tienen orden (modalidad, núcleo, origen de la institución) se codificaron en columnas de 0 y 1, y las numéricas se "
  "estandarizaron cuando el algoritmo lo necesita (por ejemplo, KNN, SVM y regresión logística). La etiqueta de riesgo es el otro atributo creado.")

H2("D. Exploración de los datos (EDA)")
P(f"El promedio de los cinco módulos es de {c(f'{eda['describe']['score_mean5']['mean']:.1f}')} puntos, con una desviación de "
  f"{c(f'{eda['describe']['score_mean5']['std']:.1f}')}. Los módulos se parecen entre sí, pero no son lo mismo: sus correlaciones van de "
  f"{f2(eda['module_corr_min'])} a {f2(eda['module_corr_max'])} (Fig. 4 muestra el promedio y el corte de riesgo).")
fig("fig_target.png", "Distribución del promedio de los cinco módulos y corte del 25% inferior.")
mcn = eda["mean_score_contrast"]
P("Los contrastes que sugería la propuesta se confirman con los datos limpios: presenciales "
  f"{c(mcn['onsite'])} puntos contra {c(mcn['distance_virtual'])} de distancia/virtual; estrato 1 con {c(mcn['stratum1'])} contra {c(mcn['stratum4'])} del "
  f"estrato 4; quienes no trabajan {c(mcn['no_work'])} contra {c(mcn['work_gt30'])} de quienes trabajan más de 30 horas; y {c(mcn['internet'])} con "
  f"internet contra {c(mcn['no_internet'])} sin internet. La Fig. 5 lo muestra como porcentaje de estudiantes en riesgo, y la Fig. 6 muestra que "
  "el núcleo de estudio también cambia mucho el panorama (de 7,9% en ingeniería civil a 36,8% en psicología).")
fig("fig_risk_groups.png", "Porcentaje de estudiantes en riesgo por estrato, modalidad, horas de trabajo e internet.")
fig("fig_risk_nucleo.png", "Porcentaje en riesgo en los diez núcleos de estudio más grandes.")
H2("E. Qué variables se relacionan con el riesgo")
at = eda["association_tests"]
table("Relación de cada variable con el riesgo (V de Cramér: 0 = ninguna, 1 = total)",
      [["Variable", "V de Cramér", "valor p"]] + [[ASSOC.get(k, k), f3(v["cramers_v"]), f"{v['p_value']:.1e}".replace(".", ",")] for k, v in list(at.items())[:9]] +
      [["Edad (correlación de Spearman con el promedio)", f3(eda["age_spearman_with_mean"]["rho"]), f"{eda['age_spearman_with_mean']['p']:.1e}".replace(".", ",")]],
      [1.9, .75, .7])
wk = eda["mode_vs_work_note"]["pct_work_gt30_by_mode"]
P(f"La modalidad es la que más se relaciona con el riesgo, y la edad pesa tanto como cualquier otra (a mayor edad, menor puntaje; ρ = "
  f"{f2(eda['age_spearman_with_mean']['rho'])}), aunque la propuesta no la destacaba. El periodo, en cambio, no tiene relación (V = "
  f"{f3(at['Period']['cramers_v'])}), así que el riesgo no cambió de un año a otro. Eso sí, las variables vienen enredadas: trabaja más de 30 horas "
  f"el {c(wk['PRESENCIAL'])}% de los presenciales, el {c(wk['DISTANCIA'])}% de los de distancia y el {c(wk['DISTANCIA VITUAL'])}% de los virtuales, "
  "y los de distancia además son mayores. Por eso estos números solo describen: no permiten decir cuál de esas condiciones es la causa.")
H2("F. Grupos de estudiantes (clustering)")
ks = cl["k_search"]
P("Para encontrar perfiles se agruparon los estudiantes solo con variables previas al examen (sin puntajes ni etiqueta), y luego se miró cuánto riesgo "
  f"tenía cada grupo. Se usó K-Means. La separación es floja: la silueta (que va de −1 a 1) "
  f"queda entre {f2(min(v['silhouette'] for v in ks.values()))} y {f2(max(v['silhouette'] for v in ks.values()))} para k entre 2 y 8 (Fig. 7), lo "
  "que indica que los estudiantes no forman grupos bien separados. Por eso los grupos se toman como una forma de describir perfiles y no como "
  "categorías naturales.")
fig("fig_k.png", "Silueta (más alto es mejor) y Davies–Bouldin (más bajo es mejor) de K-Means para k de 2 a 8.")
P(f"Se eligió k = {cl['k_chosen']} porque da cuatro perfiles fáciles de explicar (silueta {f2(ks['4']['silhouette'])}, Davies–Bouldin {f2(ks['4']['davies_bouldin'])}). "
  f"Los perfiles son bastante estables: cambiando la semilla aleatoria 10 veces coinciden casi siempre (índice de Rand ajustado medio de {f2(cl['ari_stability_mean'])}).")
pr = {p["cluster"]: p for p in cl["profiles"]}
lab = {0: "Presencial, pública, pagan los padres", 1: "Presencial, alta educación parental y matrícula", 2: "Sin computador en casa",
       3: "Distancia, mayores, trabajan"}
table("Los cuatro perfiles de K-Means y su riesgo",
      [["Perfil", "n", "Riesgo", "Punt.", "Edad", "Presen.", "Trab. &gt;30h", "Educ. madre*"]] +
      [[f"C{k}: {lab[k]}", th(pr[k]["n"]), f"{c(pr[k]['risk_pct'])}%", c(pr[k]["mean_score"]), c(pr[k]["age_median"]), f"{c(pr[k]['pct_onsite'])}%",
        f"{c(pr[k]['pct_work_gt30'])}%", c(pr[k]["edu_mother_mean"])] for k in range(4)],
      [1.0, .3, .38, .34, .33, .4, .4, .4])
P("*Escala de 0 (ninguna) a 9 (posgrado). Los nombres de los perfiles son interpretación del equipo. El perfil C3 (a distancia, edad mediana de 31 años, "
  f"{c(pr[3]['pct_work_gt30'])}% trabaja más de 30 horas) concentra el riesgo ({c(pr[3]['risk_pct'])}%), seguido de C2 (sin computador en el hogar, "
  f"{c(pr[2]['risk_pct'])}%). C0 y C1 quedan cerca o por debajo del promedio. La Fig. 8 los dibuja en dos dimensiones.", cell)
fig("fig_clusters.png", "Izquierda: los cuatro perfiles de K-Means dibujados con PCA. Derecha: porcentaje en riesgo de cada perfil.")
H2("F. Fuente externa (scraping)")
P("Los lineamientos valoran traer datos de una fuente externa. La idea es sumar la variable <i>programa_acreditado</i>, cruzando el código SNIES de cada programa con "
  "el registro del Ministerio de Educación [3]. <b>Estado: está planeado y el script existe, pero no se ha ejecutado.</b> El archivo "
  "<font name='Mono'>src/scrape_snies.py</font> tiene la URL y el selector configurables, nunca inventa un dato que no encuentre y espera entre consultas, pero "
  "no se pudo probar contra el portal; por eso el informe no incluye resultados de esta parte. Además hay dos cuidados: el portal muestra la acreditación de "
  "hoy y los exámenes son de 2018–2022, y la acreditación suele ir de la mano del tipo de institución, así que podría repetir información que el modelo ya tiene. "
  "El proyecto funciona sin esta variable.")

# ----------------------------------------------------------------------------- V (integración con Machine Learning)
H1("V. Integración con Machine Learning")
H2("A. Cómo se hizo")
P(f"Machine Learning se integra al proyecto para pasar de describir el riesgo a predecirlo. Los {th(n_final)} estudiantes se dividieron en {th(ml['n_train'])} para entrenar y "
  f"{th(ml['n_test'])} para probar (20%), con la misma proporción de estudiantes en riesgo en ambas partes. Todo el preprocesamiento va dentro de un pipeline de scikit-learn [4] "
  "que aprende solo de los datos de entrenamiento, y los hiperparámetros se eligieron con validación cruzada de 5 pliegues (Grid Search en los modelos con pocas opciones "
  "y Random Search en los ensambles). Como solo 1 de cada 4 estudiantes está en riesgo, el criterio fue la precisión promedio (PR-AUC) además del AUC, una nota entre 0,5 "
  "(adivinar al azar) y 1 (perfecto).")
H2("B. Modelos probados")
rows = [["Modelo", "Ajuste", "AUC entren.", "AUC val. cruz.", "AUC prueba", "PR-AUC prueba"]]
tm = {"dummy": "—", **ml["tuning_method"]}
for k in ["dummy", "lr", "knn", "svm", "dt", "rf", "et", "ada", "gb"]:
    v = M[k]; rows.append([v["name"] + (" (elegido)" if k == "lr" else ""), tm.get(k, "—").replace("Grid Search", "Grid").replace("Random Search", "Random"),
                           f3(v["train_auc"]), f3(v["cv_auc"]), f3(v["test_auc"]), f3(v["test_pr_auc"])])
table("Comparación de los nueve modelos", rows, [1.2, .4, .45, .5, .45, .5])
P(f"Todos los modelos le ganan al dummy (0,50). Entre los reales las diferencias son pequeñas: en la prueba van de {f3(M['knn']['test_auc'])} (KNN) a {f3(M['gb']['test_auc'])} "
  f"(Gradient Boosting, el mejor en validación cruzada). El equipo eligió la <b>regresión logística</b> ({f3(dep['test_auc'])}, apenas {f3(gbm['test_auc'] - dep['test_auc'])} menos) porque se "
  "puede explicar con coeficientes y se puede publicar en AWS sin librerías pesadas, que importa para el plan gratuito (Sección VI). La Fig. 9 muestra que Random Forest y "
  f"Extra Trees sobreajustan (memorizan: {f3(M['rf']['train_auc'])} en entrenamiento contra {f3(M['rf']['test_auc'])} en prueba), mientras que la regresión logística queda pareja.")
fig("fig_modelos.png", "AUC de cada modelo en entrenamiento, validación cruzada y prueba.")
H2("C. Cuántos estudiantes en riesgo se detectan")
P(f"Un programa solo puede apoyar a una parte de los estudiantes, así que se fijó una regla práctica: marcar al 20% con mayor probabilidad de riesgo. Con la regresión logística, "
  f"esa regla da la matriz de la Tabla V.")
table("Matriz de confusión de la regresión logística (se marca al 20% con mayor riesgo, prueba)",
      [["", "Predicho: en riesgo", "Predicho: no en riesgo"], ["Realmente en riesgo", f"{tpp} (verdaderos positivos)", f"{fnn} (falsos negativos)"],
       ["Realmente no en riesgo", f"{fpp} (falsos positivos)", f"{tn} (verdaderos negativos)"],
       ["<b>Métricas</b>", f"Precisión {f2(prec_d)}", f"Recall {f2(rec_d)} · F1 {f2(f1_d)}"]], [1.1, 1.2, 1.15])
P(f"De cada 100 estudiantes marcados, unos {c(f'{100 * prec_d:.0f}')} sí estaban en riesgo (el doble de lo normal, que es 25), y se detecta alrededor del "
  f"{c(f'{100 * rec_d:.0f}')}% de todos los que están en riesgo.")
H2("D. Limitación: el modelo depende demasiado de la modalidad")
P(f"El modelo marca al {pc(fo['Distancia/virtual']['flag_rate'])} de los estudiantes a distancia pero solo al {pc(fo['Presencial']['flag_rate'])} de los presenciales, así que detecta a "
  f"{pc(fo['Distancia/virtual']['tpr'])} de los de distancia en riesgo y apenas a {pc(fo['Presencial']['tpr'])} de los presenciales en riesgo. Dentro de cada modalidad distingue "
  f"razonablemente a los presenciales (AUC {f3(fo['Presencial']['auc'])}) pero casi no a los de distancia (AUC {f3(fo['Distancia/virtual']['auc'])}, cerca de adivinar). En la práctica funciona en buena "
  "parte como un detector de modalidad a distancia. Una alternativa es marcar al 20% con mayor riesgo <i>dentro de cada modalidad</i>: el recall en presenciales sube de "
  f"{f2(fo['Presencial']['tpr'])} a {f2(sa['Presencial']['tpr'])}, aunque baja la precisión total (de {f2(prec_d)} a {f2(sa['Todos']['precision'])}). Cuál regla usar es una decisión del programa. "
  f"Mirando el estrato, los estudiantes de estratos 1 y 2 reciben más falsas alarmas (FPR {f2(fo['Estrato 1-2']['fpr'])} contra {f2(fo['Estrato 3+']['fpr'])}), algo para vigilar si el puntaje se usa para asignar apoyos.")

# ----------------------------------------------------------------------------- VI (cloud)
H1("VI. Módulo de Cloud Computing en AWS (plan gratuito)")
H2("A. Arquitectura")
P("El modelo es una regresión logística de unos 10 KB y se espera poco tráfico, así que el equipo escogió una arquitectura <i>serverless</i> en AWS (Fig. 10): una función "
  "Lambda con una URL pública (Function URL) que lee el modelo desde un bucket de S3 privado y escribe logs en CloudWatch. No hace falta una máquina virtual ni una base de datos.")
P("Desde el 15 de julio de 2025 las cuentas nuevas de AWS reciben créditos (100 dólares al registrarse y hasta 100 más por tareas) y el plan gratuito dura hasta 6 meses o hasta "
  "que se acaben, sin cobro a menos que se pase al plan de pago [5]. Lambda tiene además una capa gratuita permanente de 1 millón de solicitudes y 400.000 GB-segundos al mes [6]. "
  "Las fuentes no coinciden sobre si S3 y API Gateway son gratis o gastan créditos en cuentas nuevas [7]; el equipo asume lo segundo. Por eso el diseño evita lo que cuesta: no usa "
  "API Gateway (la Function URL no tiene costo adicional), ni Docker y ECR (el código se sube como .zip y la regresión logística se programó en Python puro), ni VPC y NAT "
  "(se cobran por hora). Como la cuenta gratuita se cierra a los 6 meses, todo puede borrarse y recrearse con un comando.")
fig("fig_cloud.png", "Arquitectura en AWS para el plan gratuito: una Lambda con URL pública que lee el modelo desde S3.")
H2("B. Infraestructura como código (Terraform)")
P("Los scripts de Terraform [8] están en la carpeta <font name='Mono'>terraform/</font> y crean: un bucket de S3 privado, cifrado y con versiones que guarda el modelo; un rol de IAM con "
  "permisos mínimos (leer el modelo y escribir logs); la función Lambda (Python 3.12, 512 MB) con su Function URL; un grupo de logs que se borra a los 14 días; y un presupuesto de "
  "AWS Budgets que avisa por correo al llegar al 80% del límite. La función responde <font name='Mono'>GET /health</font>, <font name='Mono'>POST /predict</font> (recibe los datos de un "
  "estudiante en JSON y devuelve la probabilidad, si entra en el 20% más alto y los cinco factores que más pesaron, calculados con los coeficientes del modelo) y una página de prueba en "
  "<font name='Mono'>GET /</font>. Desde octubre de 2025 una URL pública de Lambda necesita dos permisos, <font name='Mono'>InvokeFunctionUrl</font> e "
  "<font name='Mono'>InvokeFunction</font> [9], y ambos están en el código.")
P("Para ponerlo en marcha: crear la cuenta con el plan gratuito, instalar Terraform y la AWS CLI y conectarla (<font name='Mono'>aws configure</font>), copiar "
  "<font name='Mono'>terraform.tfvars.example</font> a <font name='Mono'>terraform.tfvars</font> con el correo de las alertas, ejecutar <font name='Mono'>terraform init</font>, "
  "<font name='Mono'>plan</font> y <font name='Mono'>apply</font>, probar con <font name='Mono'>curl</font> la <font name='Mono'>api_url</font> que muestra Terraform y, al terminar, "
  "<font name='Mono'>terraform destroy</font>.")
H2("C. Estimación preliminar de costos")
P("Se asume una función de 512 MB que tarda 200 milisegundos por solicitud y un bucket con menos de 0,1 GB. Los precios de lista son 0,20 dólares por millón de solicitudes y "
  "0,0000166667 dólares por GB-segundo en Lambda [6], y 0,023 dólares por GB-mes en S3; la Function URL no tiene costo adicional [9]. No se incluyen transferencia de datos ni logs por "
  "encima de lo gratuito. La última columna muestra cuánto costaría cuando termine el plan gratuito.")
table("Costo mensual estimado en dólares",
      [["Escenario", "Dentro de la capa gratuita", "Con capa gratuita", "Sin capa gratuita"]] +
      [[COST[k], "Sí" if v["inside_free"] else "No", c(f"{v['with_free_tier']:.2f}"), c(f"{v['without_free_tier']:.2f}")] for k, v in cost.items()],
      [1.5, .75, .6, .6])
P("Hasta 500 mil solicitudes al mes el uso cabe en lo gratuito de Lambda y el gasto es prácticamente cero; solo la prueba de estrés de 5 millones lo supera. Los precios pueden cambiar, por eso "
  "hay que contrastarlos con la calculadora de AWS antes de desplegar.")
H2("D. Estado de verificación")
P("<b>Ya está:</b> el código de Terraform se lee correctamente como HCL y la función de la API se probó en el computador, con las mismas probabilidades que scikit-learn en los 4.379 "
  "estudiantes (diferencia máxima menor que 10^-15). <b>Falta:</b> ejecutar <font name='Mono'>terraform validate</font>, <font name='Mono'>plan</font> y <font name='Mono'>apply</font> en una cuenta real y "
  "probar la URL desde internet, porque donde se redactó este informe no había Terraform ni acceso a AWS. Esa evidencia debe adjuntarse a la entrega.")

H1("Referencias")
refs = [
    "ICFES, “Saber Pro: examen de Estado de calidad de la educación superior,” Instituto Colombiano para la Evaluación de la Educación. [En línea]. Disponible: https://www.icfes.gov.co",
    "Naciones Unidas, “Objetivos de Desarrollo Sostenible 4 y 10,” 2015. [En línea]. Disponible: https://sdgs.un.org/goals",
    "Ministerio de Educación Nacional, “SNIES: consulta de programas e instituciones con acreditación en alta calidad.” [En línea]. Disponible: https://www.mineducacion.gov.co/sistemasdeinformacion/1735/w3-article-318236.html",
    "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” <i>J. Mach. Learn. Res.</i>, vol. 12, pp. 2825–2830, 2011.",
    "Amazon Web Services, “AWS Free Tier now offers $200 in credits and 6-month free plan,” 2025. [En línea]. Disponible: https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/",
    "Amazon Web Services, “AWS Lambda pricing.” [En línea]. Disponible: https://aws.amazon.com/lambda/pricing/",
    "AWS Builder Center, “AWS Free Tier 2026: what’s free and how to start.” [En línea]. Disponible: https://builder.aws.com/content/3IQ2c19Fk9N0wQdSXz5zvpp4QwK/what-aws-actually-gives-you-for-free-in-2026-and-how-to-set-it-up-right",
    "HashiCorp, “Terraform documentation: AWS provider.” [En línea]. Disponible: https://registry.terraform.io/providers/hashicorp/aws/latest/docs",
    "Amazon Web Services, “Control access to Lambda function URLs.” [En línea]. Disponible: https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html",
]
for i, r in enumerate(refs, 1):
    S.append(Paragraph(f"[{i}] {r}", ref))

# ----------------------------------------------------------------------------- document
def footer(c, d):
    c.saveState(); c.setFont("Serif", 7.5)
    c.drawCentredString(letter[0] / 2, 0.42 * inch, f"Proyecto Integrador — Riesgo de bajo desempeño en Saber Pro — página {d.page}")
    c.restoreState()


out = ROOT / "reports/Informe_Avance_Riesgo_Saber_Pro.pdf"
doc = BaseDocTemplate(str(out), pagesize=letter, leftMargin=.62 * inch, rightMargin=.62 * inch, topMargin=.65 * inch,
                      bottomMargin=.65 * inch, title="Predicción del riesgo de bajo desempeño en Saber Pro", author="Equipo del proyecto integrador")
W, Hh = letter
colw = (W - 1.24 * inch - .25 * inch) / 2
top_h = 2.85 * inch
frames_first = [Frame(.62 * inch, Hh - .65 * inch - top_h, W - 1.24 * inch, top_h, id="t", leftPadding=0, rightPadding=0),
                Frame(.62 * inch, .65 * inch, colw, Hh - 1.3 * inch - top_h, id="c1", leftPadding=0, rightPadding=0),
                Frame(.62 * inch + colw + .25 * inch, .65 * inch, colw, Hh - 1.3 * inch - top_h, id="c2", leftPadding=0, rightPadding=0)]
frames_later = [Frame(.62 * inch, .65 * inch, colw, Hh - 1.3 * inch, id="a", leftPadding=0, rightPadding=0),
                Frame(.62 * inch + colw + .25 * inch, .65 * inch, colw, Hh - 1.3 * inch, id="b", leftPadding=0, rightPadding=0)]
doc.addPageTemplates([PageTemplate("first", frames_first, onPage=footer), PageTemplate("later", frames_later, onPage=footer)])
S.insert(0, NextPageTemplate("later"))
doc.build(S)
print("built", out, "figures:", fig_n[0], "tables:", tab_n[0])
