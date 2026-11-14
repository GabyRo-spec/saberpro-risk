"""AWS Lambda handler (Python 3.12, standard library only) behind a Lambda Function URL.

Routes:  GET /health   POST /predict   GET /  (tiny demo page)
The model is a logistic regression exported to JSON (model.json). It is read from S3 when MODEL_BUCKET is set
(boto3 ships with the Lambda runtime) and from the local file otherwise, so no extra libraries have to be packaged.
"""
import json
import math
import os

_M = None


def _load():
    global _M
    if _M is None:
        bucket = os.environ.get("MODEL_BUCKET")
        if bucket:
            import boto3
            body = boto3.client("s3").get_object(Bucket=bucket, Key=os.environ.get("MODEL_KEY", "models/model.json"))["Body"].read()
            _M = json.loads(body)
        else:
            with open(os.path.join(os.path.dirname(__file__), "model", "model.json")) as f:
                _M = json.load(f)
    return _M


def _num(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def vectorize(m, rec):
    """Rebuild the exact column vector the scikit-learn pipeline used (impute, indicators, scale, one-hot)."""
    nf = m["num_features"]
    raw = [_num(rec.get(f)) for f in nf]
    imputed = [r if r is not None else m["medians"][i] for i, r in enumerate(raw)]
    ind = [1.0 if raw[nf.index(f)] is None else 0.0 for f in m["indicator_features"]]
    z = [(v - mu) / sd for v, mu, sd in zip(imputed + ind, m["scaler_mean"], m["scaler_scale"])]
    for f, spec in m["cat"].items():
        val = str(rec.get(f)) if rec.get(f) is not None else "SIN_DATO"
        hit = [1.0 if val == c else 0.0 for c in spec["frequent"]]
        if spec["has_infrequent"]:
            hit.append(0.0 if any(hit) else 1.0)
        z += hit
    return z


def predict(rec):
    m = _load()
    z = vectorize(m, rec)
    contrib = [c * (v - r) for c, v, r in zip(m["coef"], z, m["ref_mean"]) ]
    logit = m["intercept"] + sum(c * v for c, v in zip(m["coef"], z))
    p = 1.0 / (1.0 + math.exp(-logit))
    by = {}
    for col, c in zip(m["columns"], contrib):
        by[col.split("=")[0].split("__")[0]] = by.get(col.split("=")[0].split("__")[0], 0.0) + c
    given = {k: v for k, v in by.items() if rec.get(k) is not None}      # explain only what the caller sent
    missing = sorted(k for k in by if rec.get(k) is None)
    top = sorted(given.items(), key=lambda kv: -abs(kv[1]))[:5]
    return {"risk_probability": round(p, 4), "high_risk_flag": p >= m["threshold_top20"],
            "flag_rule": "puntaje dentro del 20% más alto de los estudiantes",
            "main_factors": [{"variable": k, "value": rec.get(k), "pushes": "sube el riesgo" if c > 0 else "baja el riesgo",
                              "effect_log_odds": round(c, 3)} for k, c in top],
            "missing_inputs": missing,
            "note": "Descriptivo, no causal. Sirve para priorizar apoyo, nunca para restringir oportunidades."}


_PAGE = """<!doctype html><meta charset=utf-8><title>Riesgo Saber Pro</title>
<h2>Riesgo Saber Pro - demo</h2><p>Pega un JSON con las variables del estudiante y pulsa el boton.</p>
<textarea id=i rows=9 cols=70>{"estrato":2,"fami_educacionmadre":4,"horas_trabajo":3,"valor_matricula":2,"edad":24,
"estu_metodo_prgm":"PRESENCIAL","inst_origen":"OFICIAL NACIONAL","estu_genero":"F"}</textarea><br>
<button onclick="go()">Predecir</button><pre id=o></pre>
<script>async function go(){const r=await fetch('predict',{method:'POST',headers:{'content-type':'application/json'},
body:document.getElementById('i').value});document.getElementById('o').textContent=JSON.stringify(await r.json(),null,2)}</script>"""


def handler(event, context=None):
    http = event.get("requestContext", {}).get("http", {})
    method, path = http.get("method", "GET"), event.get("rawPath", "/")
    def resp(code, body, ctype="application/json"):
        return {"statusCode": code, "headers": {"content-type": ctype + "; charset=utf-8"},
                "body": body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)}
    try:
        if path.endswith("/health"):
            return resp(200, {"status": "ok"})
        if path.endswith("/predict") and method == "POST":
            return resp(200, predict(json.loads(event.get("body") or "{}")))
        if method == "GET":
            return resp(200, _PAGE, "text/html")
        return resp(404, {"error": "no encontrado"})
    except Exception as e:
        return resp(400, {"error": type(e).__name__, "detalle": str(e)[:200]})
