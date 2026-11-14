"""OPTIONAL external-source module: accreditation status of each programme (feature `programa_acreditado`).

STATUS: written but NOT executed and NOT validated against the live site (the authoring sandbox had no access to
the Ministry's domain). Before relying on it you must (1) open the SNIES programme consultation page in a browser,
(2) confirm the URL pattern and the HTML selector for the accreditation label, (3) run it on 5 known programmes.

Two methodological caveats that apply even when it runs:
  * the portal shows the CURRENT status; the exams are from 2018-2022, so status at exam time may differ;
  * accreditation is correlated with institution quality/origin, so the feature may proxy information the model
    already has (it is a confounder candidate, not a causal driver).
Usage:  python scrape_snies.py --url-template "<URL with {snies}>" --selector "<css>" --label-text "<text>"
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def fetch_status(snies: int, url_template: str, selector: str, label_text: str, session: requests.Session):
    r = session.get(url_template.format(snies=snies), timeout=30, headers={"User-Agent": "course-project/1.0"})
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    nodes = soup.select(selector)
    if not nodes:
        return None            # selector not found -> unknown, never guessed
    return int(any(label_text.lower() in n.get_text(" ", strip=True).lower() for n in nodes))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url-template", required=True)
    ap.add_argument("--selector", required=True)
    ap.add_argument("--label-text", required=True)
    ap.add_argument("--sleep", type=float, default=1.0, help="seconds between requests (be polite)")
    a = ap.parse_args()
    df = pd.read_csv(ROOT / "data/processed/saberpro_clean.csv", usecols=["ESTU_SNIES_PRGMACADEMICO"])
    codes = sorted(df.ESTU_SNIES_PRGMACADEMICO.unique())
    out, s = [], requests.Session()
    for c in codes:
        out.append({"ESTU_SNIES_PRGMACADEMICO": c,
                    "programa_acreditado": fetch_status(c, a.url_template, a.selector, a.label_text, s)})
        time.sleep(a.sleep)
    res = pd.DataFrame(out)
    res.to_csv(ROOT / "data/external/snies_accreditation.csv", index=False)
    print(res.programa_acreditado.value_counts(dropna=False))


if __name__ == "__main__":
    (ROOT / "data/external").mkdir(exist_ok=True)
    main()
