"""Step 06 (v2) - cost estimate for the AWS free-plan design (Lambda + Function URL + S3 + CloudWatch Logs).

Prices (list, us-east-1, x86): Lambda $0.20 / 1M requests and $0.0000166667 / GB-s; always-free 1M requests and 400,000 GB-s
per month. S3 Standard $0.023 / GB-month. Function URLs have no extra charge. Assumptions: 512 MB, 200 ms per request,
model + data < 0.1 GB in S3. Not modelled: data transfer out, logs above the free allowance, taxes.
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MEM, DUR, S3GB = 0.5, 0.20, 0.1
rows = {}
for name, req in {"Piloto": 5_000, "Uso por el programa": 50_000, "Uso institucional": 500_000, "Prueba de estrés": 5_000_000}.items():
    gbs = req * MEM * DUR
    lam_free = max(req - 1_000_000, 0) / 1e6 * 0.20 + max(gbs - 400_000, 0) * 0.0000166667
    lam_list = req / 1e6 * 0.20 + gbs * 0.0000166667            # as if there were no free allowance
    s3 = S3GB * 0.023
    rows[name] = {"requests": req, "gb_seconds": gbs, "inside_free": bool(req <= 1_000_000 and gbs <= 400_000),
                  "with_free_tier": round(lam_free + s3, 2), "without_free_tier": round(lam_list + s3, 2)}
(ROOT / "reports/cost_estimate.json").write_text(json.dumps(rows, indent=2))
for k, v in rows.items(): print(k, v)
