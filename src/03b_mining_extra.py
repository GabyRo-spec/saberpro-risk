"""Step 03b - course topics in unit V/VI: hierarchical clustering, DBSCAN, PCA, FP-Growth vs Apriori."""
import json, time
from pathlib import Path
import numpy as np, pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import adjusted_rand_score, davies_bouldin_score, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from features import SEED, engineer

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data/processed/saberpro_clean.csv"); X = engineer(df)
num = ["estrato", "fami_educacionpadre", "fami_educacionmadre", "horas_trabajo", "valor_matricula", "edad", "fami_tieneinternet",
       "fami_tienecomputador", "fami_tieneautomovil", "fami_tienelavadora", "estu_pagomatriculabeca", "estu_pagomatriculacredito",
       "estu_pagomatriculapadres", "estu_pagomatriculapropio"]
Z = X[num].copy(); Z["edad"] = Z["edad"].clip(upper=Z["edad"].quantile(.99))
Z["mode_onsite"] = (X.estu_metodo_prgm == "PRESENCIAL").astype(int); Z["mode_virtual"] = (X.estu_metodo_prgm == "DISTANCIA VITUAL").astype(int)
Z["female"] = (X.estu_genero == "F").astype(int)
Zs = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(Z))
out = {}
# PCA: how many components keep 80% / 90% of the variance
pca = PCA(random_state=SEED).fit(Zs); cum = np.cumsum(pca.explained_variance_ratio_)
out["pca"] = {"n_features": int(Zs.shape[1]), "components_80": int(np.argmax(cum >= .8) + 1), "components_90": int(np.argmax(cum >= .9) + 1),
              "var_2": float(cum[1])}
def prof(labels, name):
    m = labels >= 0; ks = sorted(set(labels[m]))
    d = {"method": name, "clusters": len(ks), "noise_pct": float(100 * (~m).mean())}
    if len(ks) > 1:
        d["silhouette"] = float(silhouette_score(Zs[m], labels[m], sample_size=3000, random_state=SEED)); d["davies_bouldin"] = float(davies_bouldin_score(Zs[m], labels[m]))
        d["risk_range_pct"] = [float(100 * df.risk[m][labels[m] == k].mean()) for k in ks]
    return d
km = KMeans(4, n_init=50, random_state=SEED).fit(Zs).labels_
hc = AgglomerativeClustering(4, linkage="ward").fit_predict(Zs)
res = [prof(km, "K-Means (k=4)"), prof(hc, "Jerárquico Ward (k=4)")]
out["ari_kmeans_vs_hier"] = float(adjusted_rand_score(km, hc))
# DBSCAN: eps from the k-distance curve (k = 2*dim is the usual rule; we use 30 for 17 dims)
nn = NearestNeighbors(n_neighbors=30).fit(Zs); dist = np.sort(nn.kneighbors(Zs)[0][:, -1])
best = None
for q in (.5, .7, .85, .95):
    eps = float(np.quantile(dist, q)); lab = DBSCAN(eps=eps, min_samples=30).fit_predict(Zs)
    d = prof(lab, f"DBSCAN (eps={eps:.2f}, min_samples=30)"); d["eps_quantile"] = q; res.append(d)
out["clustering_comparison"] = res
# Apriori vs FP-Growth on the same transactions (same itemsets expected; compare run time)
tx = pd.DataFrame(index=df.index)
tx["Estrato<=2"] = X.estrato <= 2; tx["Modalidad=Distancia/Virtual"] = X.estu_metodo_prgm != "PRESENCIAL"; tx["Modalidad=Presencial"] = X.estu_metodo_prgm == "PRESENCIAL"
tx["Trabajo>30h"] = X.horas_trabajo == 4; tx["SinInternet"] = X.fami_tieneinternet == 0; tx["SinComputador"] = X.fami_tienecomputador == 0
tx["EduMadre<=Primaria"] = X.fami_educacionmadre <= 2; tx["Matricula<1M"] = X.valor_matricula <= 2; tx["Edad>=30"] = X.edad >= 30
tx["Beca"] = X.estu_pagomatriculabeca == 1; tx["Mujer"] = X.estu_genero == "F"; tx["Privada"] = df.INST_ORIGEN.str.startswith("NO OFICIAL")
tx = tx.fillna(False).astype(bool); tx["RIESGO"] = df.risk.astype(bool)
t0 = time.time(); a = apriori(tx, min_support=.03, use_colnames=True, max_len=4); ta = time.time() - t0
t0 = time.time(); f = fpgrowth(tx, min_support=.03, use_colnames=True, max_len=4); tf_ = time.time() - t0
sa = {frozenset(x) for x in a.itemsets}; sf = {frozenset(x) for x in f.itemsets}
out["apriori_vs_fpgrowth"] = {"itemsets_apriori": len(sa), "itemsets_fpgrowth": len(sf), "same_itemsets": sa == sf,
                              "seconds_apriori": round(ta, 3), "seconds_fpgrowth": round(tf_, 3)}
(ROOT / "reports/mining_extra.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
print(json.dumps(out, indent=1, ensure_ascii=False))
