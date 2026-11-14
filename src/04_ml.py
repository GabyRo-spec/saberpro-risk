"""Step 04 (v2) - Machine Learning following the course syllabus (units I-VI).

Models: dummy, logistic regression, KNN, SVM, decision tree, random forest, extra trees, AdaBoost, gradient boosting.
Tuning: Grid Search (small grids) and Random Search (ensembles). Metrics: confusion matrix, precision, recall, F1, ROC.
Deployed model: logistic regression (can be served in pure Python on AWS Lambda without heavy libraries).
Outputs: reports/ml_results.json, figures_es/*.png, models/risk_model.joblib, api/model/model.json
"""
import json
import warnings
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (AdaBoostClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier,
                              RandomForestClassifier)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix, f1_score, fbeta_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold, cross_val_predict, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from features import CAT_FEATURES, NUM_FEATURES, SEED, engineer

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports/figures_es"
FIG.mkdir(parents=True, exist_ok=True)
(ROOT / "models").mkdir(exist_ok=True)
(ROOT / "api/model").mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "figure.dpi": 200, "axes.spines.top": False,
                     "axes.spines.right": False})

df = pd.read_csv(ROOT / "data/processed/saberpro_clean.csv")
X = engineer(df)
y = df.risk.values
R = {"n": int(len(df)), "prevalence": float(y.mean())}


def prep(num, cat, scale):
    ntf = [("imp", SimpleImputer(strategy="median", add_indicator=True))]
    if scale:
        ntf.append(("sc", StandardScaler()))
    return ColumnTransformer([
        ("num", Pipeline(ntf), num),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=30, sparse_output=False), cat)])


def make(model, num=NUM_FEATURES, cat=CAT_FEATURES, scale=False):
    return Pipeline([("prep", prep(num, cat, scale)), ("clf", model)])


Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.2, stratify=y, random_state=SEED)
R["n_train"], R["n_test"] = int(len(Xtr)), int(len(Xte))
cv = StratifiedKFold(5, shuffle=True, random_state=SEED)

# ---- models and search spaces ----------------------------------------------------------------
NAMES = {  # key -> Spanish display name
    "dummy": "Dummy (prevalencia)", "lr": "Regresión logística", "knn": "KNN", "svm": "SVM", "dt": "Árbol de decisión",
    "rf": "Random Forest", "et": "Extra Trees", "ada": "AdaBoost", "gb": "Gradient Boosting"}
base = {
    "dummy": make(DummyClassifier(strategy="prior")),
    "lr": make(LogisticRegression(max_iter=3000), scale=True),
    "knn": make(KNeighborsClassifier(), scale=True),
    "svm": make(SVC(kernel="rbf", probability=True, random_state=SEED), scale=True),
    "dt": make(DecisionTreeClassifier(random_state=SEED)),
    "rf": make(RandomForestClassifier(300, n_jobs=-1, random_state=SEED)),
    "et": make(ExtraTreesClassifier(300, n_jobs=-1, random_state=SEED)),
    "ada": make(AdaBoostClassifier(random_state=SEED)),
    "gb": make(HistGradientBoostingClassifier(random_state=SEED)),
}
grid = {  # Grid Search
    "lr": {"clf__C": [.03, .1, .3, 1, 3]},
    "knn": {"clf__n_neighbors": [15, 25, 35, 51, 75]},
    "svm": {"clf__C": [.3, 1, 3], "clf__gamma": ["scale", .003]},
    "dt": {"clf__max_depth": [3, 4, 5, 6], "clf__min_samples_leaf": [20, 50]},
}
rand = {  # Random Search
    "rf": {"clf__min_samples_leaf": [5, 10, 20, 40], "clf__max_features": ["sqrt", .3, .5], "clf__max_depth": [None, 6, 10]},
    "et": {"clf__min_samples_leaf": [5, 10, 20, 40], "clf__max_features": ["sqrt", .3, .5], "clf__max_depth": [None, 6, 10]},
    "ada": {"clf__n_estimators": [50, 100, 200, 300], "clf__learning_rate": [.03, .1, .3, 1]},
    "gb": {"clf__learning_rate": [.03, .05, .1], "clf__max_depth": [2, 3, 4], "clf__max_iter": [150, 250, 400],
           "clf__l2_regularization": [0, 1, 5], "clf__min_samples_leaf": [20, 40, 80]},
}
R["tuning"], R["tuning_method"] = {}, {}
models = {}
for k, m in base.items():
    if k in grid:
        s = GridSearchCV(m, grid[k], scoring="average_precision", cv=cv, n_jobs=-1).fit(Xtr, ytr); R["tuning_method"][k] = "Grid Search"
    elif k in rand:
        s = RandomizedSearchCV(m, rand[k], n_iter=10, scoring="average_precision", cv=cv, random_state=SEED, n_jobs=-1).fit(Xtr, ytr)
        R["tuning_method"][k] = "Random Search"
    else:
        models[k] = m; continue
    models[k] = s.best_estimator_
    R["tuning"][k] = {a.replace("clf__", ""): (b.item() if isinstance(b, np.generic) else b) for a, b in s.best_params_.items()}
    print("tuned", k, R["tuning"][k], flush=True)

# ---- CV (out-of-fold), train and test metrics -------------------------------------------------------
def thr_f2(yt, p):
    pr, rc, th = precision_recall_curve(yt, p)
    f2 = (5 * pr * rc) / np.maximum(4 * pr + rc, 1e-9)
    return float(th[np.nanargmax(f2[:-1])])

oof, fitted = {}, {}
R["models"] = {}
for k, m in models.items():
    p_oof = cross_val_predict(m, Xtr, ytr, cv=cv, method="predict_proba")[:, 1]
    oof[k] = p_oof
    m.fit(Xtr, ytr); fitted[k] = m
    p_tr = m.predict_proba(Xtr)[:, 1]; p = m.predict_proba(Xte)[:, 1]
    t = thr_f2(ytr, p_oof) if k != "dummy" else .5
    yh = (p >= t).astype(int); tn, fp, fn, tp = confusion_matrix(yte, yh, labels=[0, 1]).ravel()
    R["models"][k] = {"name": NAMES[k], "train_auc": float(roc_auc_score(ytr, p_tr)), "cv_auc": float(roc_auc_score(ytr, p_oof)),
                      "cv_pr_auc": float(average_precision_score(ytr, p_oof)), "test_auc": float(roc_auc_score(yte, p)),
                      "test_pr_auc": float(average_precision_score(yte, p)), "brier": float(brier_score_loss(yte, p)),
                      "threshold_f2": t, "precision": float(precision_score(yte, yh, zero_division=0)),
                      "recall": float(recall_score(yte, yh)), "f1": float(f1_score(yte, yh)), "tp": int(tp), "fp": int(fp),
                      "fn": int(fn), "tn": int(tn)}
    print(k, {a: round(b, 3) for a, b in R["models"][k].items() if isinstance(b, float)}, flush=True)
real = [k for k in models if k != "dummy"]
R["best_by_cv_prauc"] = max(real, key=lambda k: R["models"][k]["cv_pr_auc"])
DEPLOY = "lr"
R["deployed_model"] = DEPLOY

# ---- figure: train vs CV vs test AUC (overfitting / underfitting) ---------------------------------------
order = sorted(real, key=lambda k: R["models"][k]["test_auc"])
fig, ax = plt.subplots(figsize=(3.4, 2.5)); yy = np.arange(len(order)); h = .26
for j, (key, lab, col) in enumerate([("train_auc", "Entrenamiento", "#c0504d"), ("cv_auc", "Validación cruzada", "#7f7f7f"),
                                      ("test_auc", "Prueba", "#1f4e79")]):
    ax.barh(yy + (j - 1) * h, [R["models"][k][key] for k in order], h, label=lab, color=col)
ax.set_yticks(yy); ax.set_yticklabels([NAMES[k] for k in order]); ax.set_xlim(.5, 1.0); ax.set_xlabel("AUC")
ax.legend(frameon=False, fontsize=5.5, loc="lower right"); ax.set_title("AUC en entrenamiento, validación y prueba")
fig.tight_layout(); fig.savefig(FIG / "fig_modelos.png"); plt.close()

# ---- operating points for the deployed model --------------------------------------------------------------------
pd_ = fitted[DEPLOY].predict_proba(Xte)[:, 1]
t20 = float(np.percentile(oof[DEPLOY], 80))
flag = (pd_ >= t20).astype(int)
R["deploy_top20"] = {"threshold": t20, "flagged_pct": float(flag.mean() * 100), "precision": float(precision_score(yte, flag)),
                     "recall": float(recall_score(yte, flag)), "lift": float(precision_score(yte, flag) / yte.mean())}
onsite_tr = (Xtr.estu_metodo_prgm == "PRESENCIAL").values; onsite_te = (Xte.estu_metodo_prgm == "PRESENCIAL").values
thr_g = {g: float(np.percentile(oof[DEPLOY][onsite_tr == g], 80)) for g in (True, False)}
flag_s = np.array([p >= thr_g[g] for p, g in zip(pd_, onsite_te)]).astype(int)

def rowstat(label, m, fl):
    tn, fp, fn, tp = confusion_matrix(yte[m], fl[m], labels=[0, 1]).ravel()
    return {"group": label, "n": int(m.sum()), "base_rate": float(yte[m].mean()), "flag_rate": float(fl[m].mean()),
            "tpr": float(tp / max(tp + fn, 1)), "fpr": float(fp / max(fp + tn, 1)), "precision": float(tp / max(tp + fp, 1)),
            "auc": float(roc_auc_score(yte[m], pd_[m])) if len(np.unique(yte[m])) == 2 else None}
allm = np.ones(len(yte), bool); g_ = Xte.estu_genero.values
groups = {"Mujer": g_ == "F", "Hombre": g_ == "M", "Estrato 1-2": (Xte.estrato <= 2).values, "Estrato 3+": (Xte.estrato >= 3).values,
          "Presencial": onsite_te, "Distancia/virtual": ~onsite_te}
R["fairness_top20"] = [rowstat("Todos", allm, flag)] + [rowstat(n, m, flag) for n, m in groups.items()]
R["stratified_top20"] = [rowstat("Todos", allm, flag_s), rowstat("Presencial", onsite_te, flag_s), rowstat("Distancia/virtual", ~onsite_te, flag_s)]
cm = confusion_matrix(yte, flag, labels=[0, 1]); R["deploy_confusion_top20"] = cm.tolist()
# capture curve
o = np.argsort(-pd_); R["topk"] = {f"{k}": {"precision": float(yte[o[:int(len(o) * k / 100)]].mean()),
                                            "captured_pct": float(yte[o[:int(len(o) * k / 100)]].sum() / yte.sum() * 100)} for k in (10, 20, 30)}

# ---- curves (ROC, PR, calibration) -----------------------------------------------------------------------------------
fig, axs = plt.subplots(2, 2, figsize=(3.4, 3.2)); axs = axs.ravel()
for k, col in [("lr", "#1f4e79"), ("rf", "#4f9d69"), ("knn", "#e0a030"), ("dt", "#7f7f7f")]:
    p = fitted[k].predict_proba(Xte)[:, 1]
    f, t_, _ = roc_curve(yte, p); axs[0].plot(f, t_, color=col, lw=1, label=NAMES[k])
    pr, rc, _ = precision_recall_curve(yte, p); axs[1].plot(rc, pr, color=col, lw=1)
    fp_, mp_ = calibration_curve(yte, p, n_bins=8, strategy="quantile"); axs[2].plot(mp_, fp_, "o-", color=col, lw=.8, ms=2)
axs[0].plot([0, 1], [0, 1], "k:", lw=.6); axs[0].set_title("Curva ROC"); axs[0].set_xlabel("Falsos positivos"); axs[0].set_ylabel("Verdaderos positivos")
axs[1].axhline(yte.mean(), color="k", ls=":", lw=.6); axs[1].set_title("Precisión-exhaustividad"); axs[1].set_xlabel("Exhaustividad"); axs[1].set_ylabel("Precisión")
axs[2].plot([0, 1], [0, 1], "k:", lw=.6); axs[2].set_title("Calibración"); axs[2].set_xlabel("Probabilidad predicha"); axs[2].set_ylabel("Frecuencia observada")
h_, l_ = axs[0].get_legend_handles_labels(); axs[3].axis("off"); axs[3].legend(h_, l_, frameon=False, fontsize=6.5, loc="center")
fig.tight_layout(); fig.savefig(FIG / "fig_curvas.png"); plt.close()

# ---- interpretability: permutation importance on original columns (deployed model) ------------------------------------
pi = permutation_importance(fitted[DEPLOY], Xte, yte, scoring="roc_auc", n_repeats=20, random_state=SEED)
pretty = {"estu_metodo_prgm": "Modalidad", "edad": "Edad", "estu_nucleo_pregrado": "Núcleo de estudio", "fami_educacionmadre": "Educación madre",
          "valor_matricula": "Valor matrícula", "horas_trabajo": "Horas de trabajo", "fami_educacionpadre": "Educación padre",
          "inst_origen": "Origen institución", "estrato": "Estrato", "estu_genero": "Género", "inst_caracter_academico": "Carácter institución",
          "periodo": "Periodo", "fami_tienecomputador": "Tiene computador", "fami_tieneinternet": "Tiene internet",
          "estu_pagomatriculapropio": "Paga matrícula propia", "estu_pagomatriculabeca": "Beca", "estu_pagomatriculapadres": "Padres pagan",
          "estu_pagomatriculacredito": "Crédito", "fami_tieneautomovil": "Tiene automóvil", "fami_tienelavadora": "Tiene lavadora"}
imp = pd.Series(pi.importances_mean, index=X.columns).sort_values(ascending=False)
R["perm_importance"] = {k: float(v) for k, v in imp.head(12).items()}
top = imp.head(10)[::-1]
fig, ax = plt.subplots(figsize=(3.4, 2.4))
ax.barh([pretty.get(i, i) for i in top.index], top.values, xerr=pi.importances_std[[list(X.columns).index(i) for i in top.index]],
        color="#1f4e79", error_kw=dict(lw=.6, capsize=1.5))
ax.set_xlabel("Caída del AUC al mezclar la variable (prueba)"); ax.set_title("Qué variables pesan más (regresión logística)")
fig.tight_layout(); fig.savefig(FIG / "fig_importancia.png"); plt.close()

# ---- feature-selection check (ablation) with the deployed model ----------------------------------------------------------
def cv_auc(num, cat):
    m = make(LogisticRegression(C=R["tuning"]["lr"]["C"], max_iter=3000), num=num, cat=cat, scale=True)
    p = cross_val_predict(m, Xtr, ytr, cv=cv, method="predict_proba")[:, 1]
    return float(roc_auc_score(ytr, p)), float(average_precision_score(ytr, p))
no = lambda l, *x: [c for c in l if c not in x]
R["ablation"] = {
    "Todas las variables": cv_auc(NUM_FEATURES, CAT_FEATURES),
    "Sin género": cv_auc(NUM_FEATURES, no(CAT_FEATURES, "estu_genero")),
    "Sin modalidad": cv_auc(NUM_FEATURES, no(CAT_FEATURES, "estu_metodo_prgm")),
    "Sin edad": cv_auc(no(NUM_FEATURES, "edad"), CAT_FEATURES),
    "Sin modalidad ni edad": cv_auc(no(NUM_FEATURES, "edad"), no(CAT_FEATURES, "estu_metodo_prgm")),
    "Sin núcleo de estudio": cv_auc(NUM_FEATURES, no(CAT_FEATURES, "estu_nucleo_pregrado")),
    "Sin periodo": cv_auc(NUM_FEATURES, no(CAT_FEATURES, "periodo")),
    "Solo socioeconómicas y de financiación": cv_auc(no(NUM_FEATURES, "edad"), ["estu_genero"]),
}
# ---- logistic regression: direction of main effects (odds ratio per +1 SD for numeric features) ---------------------------
lr = fitted[DEPLOY]; names = list(lr.named_steps["prep"].get_feature_names_out()); coef = lr.named_steps["clf"].coef_[0]
orr = {n.replace("num__", ""): float(np.exp(c)) for n, c in zip(names, coef) if n.startswith("num__") and not n.startswith("num__missingindicator")}
R["odds_ratio_per_sd"] = {k: round(v, 3) for k, v in sorted(orr.items(), key=lambda kv: -abs(np.log(kv[1])))[:8]}

# ---- secondary task: English B1+ ------------------------------------------------------------------------------------------
y2 = df.english_b1plus.values
X2tr, X2te, y2tr, y2te = train_test_split(X, y2, test_size=.2, stratify=y2, random_state=SEED)
m2 = make(LogisticRegression(C=R["tuning"]["lr"]["C"], max_iter=3000), scale=True).fit(X2tr, y2tr); p2 = m2.predict_proba(X2te)[:, 1]
R["secondary_english_b1"] = {"prevalence": float(y2.mean()), "roc_auc": float(roc_auc_score(y2te, p2)), "pr_auc": float(average_precision_score(y2te, p2))}

# ---- refit deployed model on ALL data and export a dependency-free JSON ------------------------------------------------------
final = make(LogisticRegression(C=R["tuning"]["lr"]["C"], max_iter=3000), scale=True).fit(X, y)
joblib.dump({"model": final, "threshold_top20": t20, "features": list(X.columns)}, ROOT / "models/risk_model.joblib")
prep_ = final.named_steps["prep"]; clf = final.named_steps["clf"]
num_t = prep_.named_transformers_["num"]; imp_ = num_t.named_steps["imp"]; sc = num_t.named_steps["sc"]
enc = prep_.named_transformers_["cat"]
ind_feats = [NUM_FEATURES[i] for i in imp_.indicator_.features_]
cat_spec = {}
for i, f in enumerate(CAT_FEATURES):
    cats = [str(c) for c in enc.categories_[i]]; inf = enc.infrequent_categories_[i]
    inf = [] if inf is None else [str(c) for c in inf]
    cat_spec[f] = {"frequent": [c for c in cats if c not in inf], "has_infrequent": len(inf) > 0}
Xt = prep_.transform(X)
cols = list(NUM_FEATURES) + [f + "__missing" for f in ind_feats]
for f in CAT_FEATURES:
    cols += [f"{f}={c}" for c in cat_spec[f]["frequent"]] + ([f"{f}=__otros__"] if cat_spec[f]["has_infrequent"] else [])
assert len(cols) == Xt.shape[1] == len(clf.coef_[0]), (len(cols), Xt.shape, len(clf.coef_[0]))
model_json = {"num_features": NUM_FEATURES, "medians": imp_.statistics_.tolist(), "indicator_features": ind_feats,
              "scaler_mean": sc.mean_.tolist(), "scaler_scale": sc.scale_.tolist(), "cat": cat_spec, "columns": cols,
              "coef": clf.coef_[0].tolist(), "intercept": float(clf.intercept_[0]), "ref_mean": Xt.mean(axis=0).tolist(),
              "threshold_top20": t20, "allowed": {f: cat_spec[f]["frequent"] for f in CAT_FEATURES}}
(ROOT / "api/model/model.json").write_text(json.dumps(model_json))
Xte.assign(y=yte, p=pd_).to_csv(ROOT / "data/processed/test_predictions.csv", index=False)
(ROOT / "reports/ml_results.json").write_text(json.dumps(R, indent=2, ensure_ascii=False))
print("best by CV PR-AUC:", R["best_by_cv_prauc"], "| deployed:", DEPLOY)
print(json.dumps({k: R[k] for k in ["deploy_top20", "stratified_top20", "ablation", "odds_ratio_per_sd", "perm_importance"]}, indent=1, ensure_ascii=False))
