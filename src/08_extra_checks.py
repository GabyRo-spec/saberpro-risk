"""Step 08 (v2) - who was removed for invalid scores (share by period / mode)."""
import json
from pathlib import Path
import pandas as pd
from features import SCORE_COLS
ROOT = Path(__file__).resolve().parents[1]
raw = pd.read_csv(ROOT / "data/raw/saberpro_raw.csv").drop_duplicates().drop_duplicates("ESTU_CONSECUTIVO")
raw = raw[raw.ESTU_ESTADOINVESTIGACION == "PUBLICAR"]
inv = raw[SCORE_COLS].mask(raw[SCORE_COLS] == 0).isna().any(axis=1)
out = {"n_invalid": int(inv.sum()), "invalid_share_by_period_pct": (100 * inv.groupby(raw.PERIODO).mean()).round(1).to_dict(),
       "invalid_share_by_mode_pct": (100 * inv.groupby(raw.ESTU_METODO_PRGM).mean()).round(1).to_dict()}
(ROOT / "reports/extra_checks.json").write_text(json.dumps(out, indent=2)); print(out)
