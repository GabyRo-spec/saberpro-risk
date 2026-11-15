"""Fuente externa OPCIONAL: acreditación de alta calidad de cada programa (variable `programa_acreditado`).

Lee los códigos SNIES de data/processed/saberpro_clean.csv, consulta cada uno en el portal y guarda
data/external/snies_accreditation.csv con: código, programa_acreditado (1/0/vacío), http_status, nota.
Nunca inventa un dato: si la página no responde o no se encuentra el selector, queda vacío.

Pasos antes de correrlo completo (hay que hacerlos desde un computador con acceso al portal):
  1. Abrir en el navegador la consulta de programas del SNIES, buscar un programa conocido y, con F12 (pestaña
     Red / Network), ver de dónde salen los datos: si es una página HTML (--mode html) o una respuesta JSON (--mode json).
  2. Probar con 5 programas:   python scrape_snies.py ... --limit 5
  3. Verificar a mano esos 5 contra el portal. Si coinciden, correr sin --limit (usa --resume si se corta).

Ejemplos:
  python scrape_snies.py --mode html --url-template "https://.../programa/{snies}" --selector "css" --label-text "Alta Calidad"
  python scrape_snies.py --mode json --url-template "https://.../api/programa/{snies}" --json-key "data.acreditado" --label-text "Si"

Cuidados metodológicos (aplican aunque funcione):
  * el portal muestra la acreditación de HOY y los exámenes son de 2018-2022;
  * la acreditación suele ir de la mano del tipo de institución: puede repetir información que el modelo ya tiene.
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/snies_accreditation.csv"
HEADERS = {"User-Agent": "proyecto-academico-usta/1.0 (contacto: estudiante)"}


def _dig(obj, path):
    """Entra en un JSON con una ruta tipo 'data.acreditado'. Devuelve None si no existe."""
    for k in path.split("."):
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return None
    return obj


def fetch_status(snies, a, session):
    """Devuelve (programa_acreditado, http_status, nota). programa_acreditado es 1, 0 o None (desconocido)."""
    url = a.url_template.format(snies=snies)
    last = (None, None, "sin respuesta")
    for intento in range(3):
        try:
            r = session.get(url, timeout=30, headers=HEADERS)
        except requests.RequestException as e:
            last = (None, None, f"error de red: {type(e).__name__}")
            time.sleep(2 * (intento + 1))
            continue
        if r.status_code != 200:
            return None, r.status_code, "respuesta no exitosa"
        if a.mode == "json":
            try:
                val = _dig(r.json(), a.json_key)
            except ValueError:
                return None, 200, "la respuesta no es JSON"
            if val is None:
                return None, 200, "json_key no encontrado"
            return int(str(val).strip().lower() == a.label_text.strip().lower()), 200, ""
        nodes = BeautifulSoup(r.text, "html.parser").select(a.selector)
        if not nodes:
            return None, 200, "selector no encontrado"
        txt = " ".join(n.get_text(" ", strip=True) for n in nodes).lower()
        return int(a.label_text.lower() in txt), 200, ""
    return last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url-template", required=True, help="URL con {snies} donde va el código")
    ap.add_argument("--mode", choices=["html", "json"], default="html")
    ap.add_argument("--selector", help="selector CSS (modo html)")
    ap.add_argument("--json-key", help="ruta al campo, ej. data.acreditado (modo json)")
    ap.add_argument("--label-text", required=True, help="texto (html) o valor exacto (json) que indica acreditado")
    ap.add_argument("--sleep", type=float, default=1.0, help="segundos entre consultas")
    ap.add_argument("--limit", type=int, help="solo los primeros N códigos (para probar)")
    ap.add_argument("--resume", action="store_true", help="no repetir códigos ya guardados")
    a = ap.parse_args()
    if a.mode == "html" and not a.selector:
        ap.error("--selector es obligatorio en modo html")
    if a.mode == "json" and not a.json_key:
        ap.error("--json-key es obligatorio en modo json")

    df = pd.read_csv(ROOT / "data/processed/saberpro_clean.csv", usecols=["ESTU_SNIES_PRGMACADEMICO"])
    codes = sorted(df.ESTU_SNIES_PRGMACADEMICO.dropna().astype(int).unique())
    if a.limit:
        codes = codes[: a.limit]
    done = pd.read_csv(OUT) if (a.resume and OUT.exists()) else pd.DataFrame(
        columns=["ESTU_SNIES_PRGMACADEMICO", "programa_acreditado", "http_status", "nota"])
    ya = set(done.ESTU_SNIES_PRGMACADEMICO.astype(int))
    rows, s = done.to_dict("records"), requests.Session()
    for i, c in enumerate(codes, 1):
        if c in ya:
            continue
        v, st, nota = fetch_status(c, a, s)
        rows.append({"ESTU_SNIES_PRGMACADEMICO": c, "programa_acreditado": v, "http_status": st, "nota": nota})
        if i % 25 == 0:
            pd.DataFrame(rows).to_csv(OUT, index=False)   # guarda avance
        time.sleep(a.sleep)
    res = pd.DataFrame(rows)
    res["programa_acreditado"] = res["programa_acreditado"].astype("Int64")
    res.to_csv(OUT, index=False)
    n, ok = len(res), int(res.programa_acreditado.notna().sum())
    print(res.programa_acreditado.value_counts(dropna=False))
    print(f"Consultados: {n} | con dato: {ok} ({ok / n:.1%}) | sin dato: {n - ok}")
    if ok / n < 0.9:
        print("AVISO: menos del 90% de los programas quedó con dato; revisar URL/selector antes de usar la variable.")


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    main()
