"""Step 02 - exploratory data analysis. Writes figures to reports/figures and stats to reports/eda_stats.json."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from features import SCORE_COLS, engineer

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports/figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                     "ytick.labelsize": 6.5, "figure.dpi": 200, "axes.spines.top": False,
                     "axes.spines.right": False})
C1, C2, C3 = "#1f4e79", "#c0504d", "#7f7f7f"
W = 3.4  # column width in inches

df = pd.read_csv(ROOT / "data/processed/saberpro_clean.csv")
raw = pd.read_csv(ROOT / "data/raw/saberpro_raw.csv")
X = engineer(df)
thr = df.score_mean5.quantile(0.25)
S = {}

# Fig 1 - distribution of the derived average and threshold
fig, ax = plt.subplots(figsize=(W, 2.0))
ax.hist(df.score_mean5, bins=40, color=C1, alpha=.85)
ax.axvline(thr, color=C2, ls="--", lw=1.2)
ax.text(thr + 2, ax.get_ylim()[1] * .9, f"P25 = {thr:.1f}", color=C2, fontsize=6.5)
ax.set_xlabel("Mean of the 5 module scores"); ax.set_ylabel("Students")
ax.set_title("Derived average score and risk threshold")
fig.tight_layout(); fig.savefig(FIG / "fig_target.png"); plt.close()

# Fig 2 - invalid scores (zeros / missing) before cleaning
P = SCORE_COLS
zeros = [(raw[c] == 0).sum() for c in P]
nans = [raw[c].isna().sum() for c in P]
lab = ["Quant.", "Written", "Crit.\nreading", "English", "Citizen."]
fig, ax = plt.subplots(figsize=(W, 1.9))
ax.bar(lab, zeros, color=C2, label="score = 0")
ax.bar(lab, nans, bottom=zeros, color=C3, label="missing")
ax.set_ylabel("Records (raw file)"); ax.legend(frameon=False, fontsize=6)
ax.set_title("Invalid module scores in the raw file")
fig.tight_layout(); fig.savefig(FIG / "fig_invalid.png"); plt.close()

# Fig 3 - missingness of predictors
miss_cols = {"FAMI_TIENEAUTOMOVIL": "Car", "FAMI_TIENELAVADORA": "Washer", "FAMI_TIENECOMPUTADOR": "Computer",
             "ESTU_HORASSEMANATRABAJA": "Work hours", "FAMI_ESTRATOVIVIENDA": "Stratum",
             "FAMI_TIENEINTERNET": "Internet", "FAMI_EDUCACIONMADRE": "Mother educ.",
             "FAMI_EDUCACIONPADRE": "Father educ.", "ESTU_VALORMATRICULAUNIVERSIDAD": "Tuition"}
m = pd.Series({v: 100 * df[k].isna().mean() for k, v in miss_cols.items()}).sort_values()
fig, ax = plt.subplots(figsize=(W, 2.0))
ax.barh(m.index, m.values, color=C1)
ax.set_xlabel("% missing (clean sample)"); ax.set_title("Missing values in predictors")
fig.tight_layout(); fig.savefig(FIG / "fig_missing.png"); plt.close()

# Fig 4 - boxplots (outliers)
fig, ax = plt.subplots(figsize=(W, 2.0))
ax.boxplot([df[c] for c in P], tick_labels=["Quant.", "Written", "Crit.\nreading", "English", "Citizen."],
           flierprops=dict(marker=".", ms=2, mfc=C2, mec=C2), medianprops=dict(color=C2), widths=.55)
ax.set_ylabel("Score"); ax.set_title("Module scores, IQR outliers (kept)")
fig.tight_layout(); fig.savefig(FIG / "fig_box.png"); plt.close()

# Fig 5 - correlation among modules
corr = df[P + ["score_mean5"]].corr()
S["module_corr_min"] = round(float(corr.loc[P, P].values[np.triu_indices(5, 1)].min()), 3)
S["module_corr_max"] = round(float(corr.loc[P, P].values[np.triu_indices(5, 1)].max()), 3)
fig, ax = plt.subplots(figsize=(W, 2.5))
im = ax.imshow(corr, cmap="Blues", vmin=0, vmax=1)
nm = ["Quant.", "Written", "Crit. r.", "English", "Citizen.", "Mean"]
ax.set_xticks(range(6)); ax.set_xticklabels(nm, rotation=45, ha="right"); ax.set_yticks(range(6)); ax.set_yticklabels(nm)
for i in range(6):
    for j in range(6):
        ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=5.5,
                color="white" if corr.iloc[i, j] > .6 else "black")
ax.set_title("Pearson correlation between modules"); ax.spines[:].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig_corr.png"); plt.close()

# Risk rate by group (with 95% Wilson interval) -----------------------------------------
def risk_by(series, order=None, min_n=40):
    g = df.groupby(series).risk.agg(["mean", "sum", "count"])
    g = g[g["count"] >= min_n]
    if order is not None:
        g = g.reindex([o for o in order if o in g.index])
    z = 1.96; n = g["count"]; p = g["mean"]
    den = 1 + z**2 / n
    ctr = (p + z**2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    g["lo"], g["hi"] = ctr - half, ctr + half
    return g

groups = {
    "Stratum": (df.FAMI_ESTRATOVIVIENDA, ["Estrato 1", "Estrato 2", "Estrato 3", "Estrato 4"]),
    "Mode": (df.ESTU_METODO_PRGM, ["PRESENCIAL", "DISTANCIA", "DISTANCIA VITUAL"]),
    "Work hours/wk": (df.ESTU_HORASSEMANATRABAJA.astype(str), ["0", "Menos de 10 horas", "Entre 11 y 20 horas",
                                                                "Entre 21 y 30 horas", "Más de 30 horas"]),
    "Internet": (df.FAMI_TIENEINTERNET, ["Si", "No"]),
}
short = {"Estrato 1": "1", "Estrato 2": "2", "Estrato 3": "3", "Estrato 4": "4", "PRESENCIAL": "Onsite",
         "DISTANCIA": "Distance", "DISTANCIA VITUAL": "Virtual", "0": "0 h", "Menos de 10 horas": "<10",
         "Entre 11 y 20 horas": "11-20", "Entre 21 y 30 horas": "21-30", "Más de 30 horas": ">30",
         "Si": "Yes", "No": "No"}
fig, axs = plt.subplots(2, 2, figsize=(W, 3.0), sharey=True)
S["risk_by_group"] = {}
for ax, (name, (ser, order)) in zip(axs.ravel(), groups.items()):
    g = risk_by(ser, order)
    ax.bar([short.get(i, i) for i in g.index], 100 * g["mean"], color=C1,
           yerr=[100 * (g["mean"] - g["lo"]), 100 * (g["hi"] - g["mean"])], error_kw=dict(lw=.7, capsize=1.5))
    ax.axhline(100 * df.risk.mean(), color=C2, ls="--", lw=.8)
    ax.set_title(name, fontsize=7)
    S["risk_by_group"][name] = {str(k): {"risk_pct": round(100 * v["mean"], 1), "n": int(v["count"])}
                                for k, v in g.iterrows()}
axs[0, 0].set_ylabel("% at risk"); axs[1, 0].set_ylabel("% at risk")
fig.suptitle("Risk rate by group (dashed = overall 25%; bars = 95% CI)", fontsize=7)
fig.tight_layout(); fig.savefig(FIG / "fig_risk_groups.png"); plt.close()

# Fig 7 - risk by field of study (top 10 by size)
top = df.ESTU_NUCLEO_PREGRADO.value_counts().head(10).index
g = risk_by(df.ESTU_NUCLEO_PREGRADO).loc[top].sort_values("mean")
NM = {"INGENIERÍA CIVIL Y AFINES": "Civil engineering", "INGENIERÍA ELECTRÓNICA, TELECOMUNICACIONES Y AFINES": "Electronic/telecom eng.",
      "DERECHO Y AFINES": "Law", "INGENIERÍA DE SISTEMAS, TELEMÁTICA Y AFINES": "Systems engineering",
      "INGENIERÍA INDUSTRIAL Y AFINES": "Industrial engineering", "CONTADURÍA PUBLICA": "Public accounting",
      "INGENIERÍA AMBIENTAL, SANITARIA Y AFINES": "Environmental eng.", "ADMINISTRACIÓN": "Business administration",
      "EDUCACIÓN": "Education", "PSICOLOGÍA": "Psychology"}
lab = [NM.get(i, i.title()[:25]) for i in g.index]
fig, ax = plt.subplots(figsize=(W, 2.6))
ax.barh(lab, 100 * g["mean"], color=C1,
        xerr=[100 * (g["mean"] - g["lo"]), 100 * (g["hi"] - g["mean"])], error_kw=dict(lw=.7, capsize=1.5))
ax.axvline(100 * df.risk.mean(), color=C2, ls="--", lw=.8)
ax.set_xlabel("% at risk"); ax.set_title("Risk rate, 10 largest fields of study")
fig.tight_layout(); fig.savefig(FIG / "fig_risk_nucleo.png"); plt.close()
S["risk_by_nucleo_top10"] = {k: {"risk_pct": round(100 * v["mean"], 1), "n": int(v["count"])} for k, v in g.iterrows()}

# Statistical tests: chi-square of risk vs each categorical predictor, Cramer's V ------------------
def cramers(a, b):
    ct = pd.crosstab(a, b)
    chi2, p, _, _ = stats.chi2_contingency(ct)
    n = ct.values.sum()
    return float(np.sqrt(chi2 / (n * (min(ct.shape) - 1)))), float(p)

tests = {}
cat_view = {"Field of study": df.ESTU_NUCLEO_PREGRADO.fillna("NA"), "Study mode": df.ESTU_METODO_PRGM,
            "Institution origin": df.INST_ORIGEN, "Stratum": df.FAMI_ESTRATOVIVIENDA.fillna("NA"),
            "Mother education": df.FAMI_EDUCACIONMADRE.fillna("NA"),
            "Father education": df.FAMI_EDUCACIONPADRE.fillna("NA"),
            "Work hours": df.ESTU_HORASSEMANATRABAJA.astype(str), "Internet": df.FAMI_TIENEINTERNET.fillna("NA"),
            "Computer": df.FAMI_TIENECOMPUTADOR.fillna("NA"), "Gender": df.ESTU_GENERO,
            "Tuition": df.ESTU_VALORMATRICULAUNIVERSIDAD.fillna("NA"), "Period": df.PERIODO.astype(str)}
for k, v in cat_view.items():
    V, p = cramers(v, df.risk)
    tests[k] = {"cramers_v": round(V, 3), "p_value": float(f"{p:.2e}")}
S["association_tests"] = dict(sorted(tests.items(), key=lambda kv: -kv[1]["cramers_v"]))
r, p = stats.spearmanr(X.edad.fillna(X.edad.median()), df.score_mean5)
S["age_spearman_with_mean"] = {"rho": round(float(r), 3), "p": float(f"{p:.2e}")}

# Mean score contrasts quoted in the proposal, recomputed on the clean sample ------------------------
S["mean_score_contrast"] = {
    "onsite": round(df[df.ESTU_METODO_PRGM == "PRESENCIAL"].score_mean5.mean(), 1),
    "distance_virtual": round(df[df.ESTU_METODO_PRGM != "PRESENCIAL"].score_mean5.mean(), 1),
    "stratum1": round(df[df.FAMI_ESTRATOVIVIENDA == "Estrato 1"].score_mean5.mean(), 1),
    "stratum4": round(df[df.FAMI_ESTRATOVIVIENDA == "Estrato 4"].score_mean5.mean(), 1),
    "no_work": round(df[df.ESTU_HORASSEMANATRABAJA.astype(str) == "0"].score_mean5.mean(), 1),
    "work_gt30": round(df[df.ESTU_HORASSEMANATRABAJA == "Más de 30 horas"].score_mean5.mean(), 1),
    "no_internet": round(df[df.FAMI_TIENEINTERNET == "No"].score_mean5.mean(), 1),
    "internet": round(df[df.FAMI_TIENEINTERNET == "Si"].score_mean5.mean(), 1),
}
S["period_counts"] = df.PERIODO.value_counts().sort_index().to_dict()
S["period_risk_pct"] = (100 * df.groupby("PERIODO").risk.mean()).round(1).to_dict()
S["mode_vs_work_note"] = {
    "pct_work_gt30_by_mode": (100 * df.groupby("ESTU_METODO_PRGM").ESTU_HORASSEMANATRABAJA.apply(
        lambda s: (s == "Más de 30 horas").mean())).round(1).to_dict()}
S["describe"] = df[P + ["score_mean5"]].describe().round(2).to_dict()
(ROOT / "reports/eda_stats.json").write_text(json.dumps(S, indent=2, ensure_ascii=False, default=str))
print(json.dumps({k: S[k] for k in ["association_tests", "mean_score_contrast", "period_risk_pct",
                                    "risk_by_group", "mode_vs_work_note", "age_spearman_with_mean",
                                    "module_corr_min", "module_corr_max"]}, indent=1, ensure_ascii=False))
