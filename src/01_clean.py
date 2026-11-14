"""Step 01 - cleaning, null/outlier handling and target construction.

Input : data/raw/saberpro_raw.csv
Output: data/processed/saberpro_clean.csv, reports/cleaning_log.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from features import SCORE_COLS

ROOT = Path(__file__).resolve().parents[1]
log = {}

df = pd.read_csv(ROOT / "data/raw/saberpro_raw.csv")
log["rows_raw"] = len(df)
log["cols_raw"] = df.shape[1]

# 1. Duplicates ---------------------------------------------------------------
log["exact_duplicate_rows"] = int(df.duplicated().sum())
df = df.drop_duplicates()
log["duplicate_ids_remaining"] = int(df.ESTU_CONSECUTIVO.duplicated().sum())
# repeated IDs differ only in exam-site columns (checked in exploration) -> keep first
df = df.drop_duplicates(subset="ESTU_CONSECUTIVO", keep="first")
log["rows_after_dedup"] = len(df)

# 2. Identity not verified -----------------------------------------------------
bad_id = df.ESTU_ESTADOINVESTIGACION != "PUBLICAR"
log["identity_not_verified_removed"] = int(bad_id.sum())
df = df[~bad_id]

# 3. Invalid scores ------------------------------------------------------------
# A module score of 0 is not a real result: all 176 zeros in written communication coincide with a
# missing performance level (the essay was not graded). Same treatment for zeros elsewhere.
zero_counts = {c: int((df[c] == 0).sum()) for c in SCORE_COLS}
nan_counts = {c: int(df[c].isna().sum()) for c in SCORE_COLS}
log["zero_scores_per_module"] = zero_counts
log["nan_scores_per_module"] = nan_counts
log["comm_zero_and_missing_level"] = int(((df.MOD_COMUNI_ESCRITA_PUNT == 0) & df.MOD_COMUNI_ESCRITA_DESEM.isna()).sum())
df[SCORE_COLS] = df[SCORE_COLS].mask(df[SCORE_COLS] == 0)
invalid = df[SCORE_COLS].isna().any(axis=1)
log["rows_removed_invalid_scores"] = int(invalid.sum())
log["share_removed_invalid_scores_pct"] = round(100 * invalid.mean(), 2)
df = df[~invalid].copy()

# 4. Outliers ---------------------------------------------------------------------
out = {}
for c in SCORE_COLS:
    q1, q3 = df[c].quantile([.25, .75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    out[c] = {"lower_fence": round(float(lo), 1), "upper_fence": round(float(hi), 1),
              "n_outliers": int(((df[c] < lo) | (df[c] > hi)).sum())}
log["score_outliers_iqr"] = out  # kept: scores live in [0,300] and extremes are legitimate results

birth = pd.to_datetime(df.ESTU_FECHANACIMIENTO, format="%d/%m/%Y", errors="coerce")
age = df.PERIODO // 10 - birth.dt.year
log["age_summary"] = {k: float(v) for k, v in age.describe().round(2).items()}
log["age_lt_16_set_to_nan"] = int((age < 16).sum())
log["age_gt_50_kept"] = int((age > 50).sum())

# 5. Target -----------------------------------------------------------------------
df["score_mean5"] = df[SCORE_COLS].mean(axis=1)
thr = float(df.score_mean5.quantile(0.25))
df["risk"] = (df.score_mean5 <= thr).astype(int)
df["english_b1plus"] = df.MOD_INGLES_DESEM.isin(["B1", "B2"]).astype(int)
log["risk_threshold_p25"] = round(thr, 2)
log["risk_prevalence_pct"] = round(100 * df.risk.mean(), 2)
log["english_b1plus_prevalence_pct"] = round(100 * df.english_b1plus.mean(), 2)
log["rows_final"] = len(df)

# 6. Missing predictors (documented, not imputed here: imputation is fitted inside the ML pipeline) ----
pred_missing = ["FAMI_ESTRATOVIVIENDA", "FAMI_EDUCACIONPADRE", "FAMI_EDUCACIONMADRE", "FAMI_TIENEINTERNET",
                "FAMI_TIENECOMPUTADOR", "FAMI_TIENEAUTOMOVIL", "FAMI_TIENELAVADORA", "ESTU_HORASSEMANATRABAJA",
                "ESTU_VALORMATRICULAUNIVERSIDAD", "ESTU_PAGOMATRICULABECA", "ESTU_PAGOMATRICULACREDITO",
                "ESTU_PAGOMATRICULAPADRES", "ESTU_PAGOMATRICULAPROPIO"]
log["predictor_missing_pct"] = {c: round(100 * df[c].isna().mean(), 2) for c in pred_missing}
log["predictor_missing_by_period_pct"] = (
    df.groupby("PERIODO")[pred_missing].apply(lambda g: g.isna().mean().mean() * 100).round(2).to_dict())

# 7. Columns dropped from the modelling table ------------------------------------------
drop_cols = ["ESTU_CONSECUTIVO", "ESTU_TIPODOCUMENTO", "ESTU_TIPODOCUMENTOSB11", "ESTU_FECHANACIMIENTO",
             "ESTU_PAIS_RESIDE", "ESTU_COD_RESIDE_DEPTO", "ESTU_DEPTO_RESIDE", "ESTU_COD_RESIDE_MCPIO",
             "ESTU_MCPIO_RESIDE", "ESTU_NIVEL_PRGM_ACADEMICO", "ESTU_ESTADOINVESTIGACION", "ESTU_PRIVADO_LIBERTAD",
             "ESTU_ESTUDIANTE", "ESTU_NACIONALIDAD"]
constant = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
log["constant_columns_after_cleaning"] = constant
keep_id = df[["ESTU_CONSECUTIVO"]].copy()
df = df.drop(columns=[c for c in drop_cols if c in df.columns and c not in ("ESTU_FECHANACIMIENTO",)])
# keep birth date only to derive age inside features.engineer(); everything personal otherwise removed
df.to_csv(ROOT / "data/processed/saberpro_clean.csv", index=False)
(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports/cleaning_log.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))
print(json.dumps(log, indent=2, ensure_ascii=False))
