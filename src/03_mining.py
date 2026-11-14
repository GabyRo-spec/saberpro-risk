"""Step 03 - unsupervised mining: K-Means student profiles and association rules for risk.

Clustering uses ONLY pre-exam predictors (never scores or the target); the target is used afterwards to
profile clusters. Outputs: reports/figures/fig_clusters.png, reports/clustering.json, reports/rules.csv
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from features import SEED, engineer

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports/figures"
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "figure.dpi": 200,
                     "axes.spines.top": False, "axes.spines.right": False})
df = pd.read_csv(ROOT / "data/processed/saberpro_clean.csv")
X = engineer(df)

# ---------------------------------------------------------------- K-Means ----------------
num = ["estrato", "fami_educacionpadre", "fami_educacionmadre", "horas_trabajo", "valor_matricula", "edad",
       "fami_tieneinternet", "fami_tienecomputador", "fami_tieneautomovil", "fami_tienelavadora",
       "estu_pagomatriculabeca", "estu_pagomatriculacredito", "estu_pagomatriculapadres",
       "estu_pagomatriculapropio"]
Z = X[num].copy()
Z["edad"] = Z["edad"].clip(upper=Z["edad"].quantile(.99))                # winsorise age tail
Z["mode_onsite"] = (X.estu_metodo_prgm == "PRESENCIAL").astype(int)
Z["mode_virtual"] = (X.estu_metodo_prgm == "DISTANCIA VITUAL").astype(int)
Z["female"] = (X.estu_genero == "F").astype(int)
Z = pd.DataFrame(SimpleImputer(strategy="median").fit_transform(Z), columns=Z.columns, index=Z.index)
Zs = StandardScaler().fit_transform(Z)

res = {}
for k in range(2, 9):
    km = KMeans(k, n_init=20, random_state=SEED).fit(Zs)
    res[k] = {"inertia": float(km.inertia_), "silhouette": float(silhouette_score(Zs, km.labels_, sample_size=3000,
                                                                                random_state=SEED)),
              "davies_bouldin": float(davies_bouldin_score(Zs, km.labels_))}
K = 4  # chosen by interpretability among k with the best silhouette/DB trade-off (see report)
best = KMeans(K, n_init=50, random_state=SEED).fit(Zs)
stab = [adjusted_rand_score(best.labels_, KMeans(K, n_init=10, random_state=s).fit_predict(Zs)) for s in range(1, 11)]
df["cluster"] = best.labels_
Z["cluster"] = best.labels_
prof = Z.groupby("cluster").mean().round(2)
prof["n"] = df.groupby("cluster").size()
prof["risk_pct"] = (100 * df.groupby("cluster").risk.mean()).round(1)
prof["mean_score"] = df.groupby("cluster").score_mean5.mean().round(1)
prof["age_median"] = X.groupby(df.cluster).edad.median()
prof["pct_onsite"] = (100 * Z.groupby("cluster").mode_onsite.mean()).round(1)
prof["pct_work_gt30"] = (100 * (X.horas_trabajo == 4).groupby(df.cluster).mean()).round(1)
prof["pct_virtual"] = (100 * Z.groupby("cluster").mode_virtual.mean()).round(1)
prof["pct_beca"] = (100 * X.estu_pagomatriculabeca.groupby(df.cluster).mean()).round(1)
prof["estrato_mean"] = Z.groupby("cluster").estrato.mean().round(2)
prof["tuition_mean"] = Z.groupby("cluster").valor_matricula.mean().round(2)
prof["edu_mother_mean"] = Z.groupby("cluster").fami_educacionmadre.mean().round(2)
top_inst = df.groupby("cluster").INST_ORIGEN.agg(lambda s: s.value_counts().index[0])
prof["top_inst_origin"] = top_inst
top_nucleo = df.groupby("cluster").ESTU_NUCLEO_PREGRADO.agg(lambda s: s.value_counts().index[0])
prof["top_nucleo"] = top_nucleo
print(prof.T.to_string())

pca = PCA(2, random_state=SEED).fit(Zs)
P2 = pca.transform(Zs)
fig, axs = plt.subplots(1, 2, figsize=(3.4, 2.2), gridspec_kw={"width_ratios": [1.3, 1]})
cols = ["#1f4e79", "#c0504d", "#4f9d69", "#e0a030"]
rng = np.random.default_rng(SEED)
for c in range(K):
    m = best.labels_ == c
    axs[0].scatter(P2[m, 0], P2[m, 1], s=2.5, alpha=.4, color=cols[c], label=f"C{c}")
axs[0].set_xlabel(f"PC1 ({100 * pca.explained_variance_ratio_[0]:.0f}%)")
axs[0].set_ylabel(f"PC2 ({100 * pca.explained_variance_ratio_[1]:.0f}%)")
axs[0].legend(frameon=False, fontsize=5.5, markerscale=3, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4); axs[0].set_title("PCA view of clusters")
axs[1].bar([f"C{c}" for c in range(K)], prof.risk_pct, color=cols)
axs[1].axhline(100 * df.risk.mean(), ls="--", color="grey", lw=.8)
axs[1].set_ylabel("% at risk"); axs[1].set_title("Risk by cluster")
fig.tight_layout(); fig.savefig(FIG / "fig_clusters.png"); plt.close()

fig, ax = plt.subplots(figsize=(3.4, 1.8))
ks = list(res)
ax.plot(ks, [res[k]["silhouette"] for k in ks], "o-", color="#1f4e79", ms=3, label="Silhouette")
ax.set_xlabel("k"); ax.set_ylabel("Silhouette", color="#1f4e79")
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(ks, [res[k]["davies_bouldin"] for k in ks], "s--", color="#c0504d", ms=3)
ax2.set_ylabel("Davies-Bouldin", color="#c0504d"); ax.set_title("Choosing k for K-Means")
fig.tight_layout(); fig.savefig(FIG / "fig_k.png"); plt.close()

out = {"k_search": res, "k_chosen": K, "ari_stability_mean": float(np.mean(stab)), "ari_stability_min": float(np.min(stab)),
       "pca_var_2": float(pca.explained_variance_ratio_[:2].sum()),
       "profiles": json.loads(prof.reset_index().to_json(orient="records", force_ascii=False))}
(ROOT / "reports/clustering.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
df[["cluster"]].to_csv(ROOT / "data/processed/clusters.csv", index=False)

# --------------------------------------------------------------- association rules -----------
tx = pd.DataFrame(index=df.index)
tx["Stratum<=2"] = X.estrato <= 2
tx["Stratum>=3"] = X.estrato >= 3
tx["Mode=Onsite"] = X.estu_metodo_prgm == "PRESENCIAL"
tx["Mode=Distance/Virtual"] = X.estu_metodo_prgm != "PRESENCIAL"
tx["Work>30h"] = X.horas_trabajo == 4
tx["Work<=10h"] = X.horas_trabajo <= 1
tx["NoInternet"] = X.fami_tieneinternet == 0
tx["NoComputer"] = X.fami_tienecomputador == 0
tx["MotherEdu<=Primary"] = X.fami_educacionmadre <= 2
tx["MotherEdu>=Tertiary"] = X.fami_educacionmadre >= 5
tx["Tuition<1M"] = X.valor_matricula <= 2
tx["Tuition>=4M"] = X.valor_matricula >= 5
tx["Scholarship"] = X.estu_pagomatriculabeca == 1
tx["Age>=30"] = X.edad >= 30
tx["Age<=23"] = X.edad <= 23
tx["Private(Fund./Corp.)"] = df.INST_ORIGEN.str.startswith("NO OFICIAL")
tx["Public"] = df.INST_ORIGEN.str.startswith("OFICIAL")
tx["Female"] = X.estu_genero == "F"
tx["Male"] = X.estu_genero == "M"
tx = tx.fillna(False).astype(bool)
tx["RISK"] = df.risk.astype(bool)

fi = apriori(tx, min_support=0.03, use_colnames=True, max_len=4)
rules = association_rules(fi, metric="confidence", min_threshold=0.3)
rules = rules[rules.consequents.apply(lambda s: s == frozenset({"RISK"}))].copy()
rules = rules[rules.lift >= 1.4].sort_values(["lift", "support"], ascending=False)
rules["antecedents"] = rules.antecedents.apply(lambda s: " & ".join(sorted(s)))
# keep only the most informative rule per antecedent size to avoid redundancy: drop rules whose lift is not
# higher than that of any strict subset
rules = rules[["antecedents", "support", "confidence", "lift"]].reset_index(drop=True)
keep = []
for i, r in rules.iterrows():
    A = set(r.antecedents.split(" & "))
    redundant = any(set(q.antecedents.split(" & ")) < A and q.lift >= r.lift * 0.98 for _, q in rules.iterrows())
    keep.append(not redundant)
rules = rules[keep].reset_index(drop=True)
rules.round(3).to_csv(ROOT / "reports/rules.csv", index=False)
inv = tx[~tx.RISK].mean(); 
print("baseline risk", tx.RISK.mean().round(3), "n itemsets", len(fi), "rules", len(rules))
print(rules.head(12).round(3).to_string())
