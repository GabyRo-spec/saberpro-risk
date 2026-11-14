"""Shared constants and feature engineering for the Saber Pro risk project."""
import numpy as np
import pandas as pd

SEED = 42

SCORE_COLS = [
    "MOD_RAZONA_CUANTITAT_PUNT",
    "MOD_COMUNI_ESCRITA_PUNT",
    "MOD_LECTURA_CRITICA_PUNT",
    "MOD_INGLES_PUNT",
    "MOD_COMPETEN_CIUDADA_PUNT",
]

# Columns allowed as predictors (known before the exam). Mirrors the project proposal.
CAT_COLS = [
    "ESTU_GENERO", "ESTU_METODO_PRGM", "INST_ORIGEN", "INST_CARACTER_ACADEMICO",
    "ESTU_NUCLEO_PREGRADO", "PERIODO",
]
BIN_COLS = [
    "FAMI_TIENEINTERNET", "FAMI_TIENECOMPUTADOR", "FAMI_TIENEAUTOMOVIL", "FAMI_TIENELAVADORA",
    "ESTU_PAGOMATRICULABECA", "ESTU_PAGOMATRICULACREDITO", "ESTU_PAGOMATRICULAPADRES",
    "ESTU_PAGOMATRICULAPROPIO",
]
EDU_COLS = ["FAMI_EDUCACIONPADRE", "FAMI_EDUCACIONMADRE"]

HOURS_MAP = {"0": 0, "Menos de 10 horas": 1, "Entre 11 y 20 horas": 2,
             "Entre 21 y 30 horas": 3, "Más de 30 horas": 4}
TUITION_MAP = {"No pagó matrícula": 0, "Menos de 500 mil": 1, "Entre 500 mil y menos de 1 millón": 2,
               "Entre 1 millón y menos de 2.5 millones": 3, "Entre 2.5 millones y menos de 4 millones": 4,
               "Entre 4 millones y menos de 5.5 millones": 5, "Entre 5.5 millones y menos de 7 millones": 6,
               "Más de 7 millones": 7}
EDU_MAP = {"Ninguno": 0, "Primaria incompleta": 1, "Primaria completa": 2,
           "Secundaria (Bachillerato) incompleta": 3, "Secundaria (Bachillerato) completa": 4,
           "Técnica o tecnológica incompleta": 5, "Técnica o tecnológica completa": 6,
           "Educación profesional incompleta": 7, "Educación profesional completa": 8, "Postgrado": 9}
ESTRATO_MAP = {"Estrato 1": 1, "Estrato 2": 2, "Estrato 3": 3, "Estrato 4": 4, "Estrato 5": 5, "Estrato 6": 6}
YESNO = {"Si": 1, "No": 0}


def engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Return a model-ready feature frame (NaN kept where information is truly missing)."""
    X = pd.DataFrame(index=df.index)
    X["estrato"] = df["FAMI_ESTRATOVIVIENDA"].map(ESTRATO_MAP)          # 'Sin Estrato' -> NaN
    for c in EDU_COLS:
        X[c.lower()] = df[c].map(EDU_MAP)                                 # 'No sabe'/'No Aplica' -> NaN
    X["horas_trabajo"] = df["ESTU_HORASSEMANATRABAJA"].astype("string").map(HOURS_MAP)
    X["valor_matricula"] = df["ESTU_VALORMATRICULAUNIVERSIDAD"].map(TUITION_MAP)
    for c in BIN_COLS:
        X[c.lower()] = df[c].map(YESNO)
    birth = pd.to_datetime(df["ESTU_FECHANACIMIENTO"], format="%d/%m/%Y", errors="coerce")
    age = df["PERIODO"] // 10 - birth.dt.year
    X["edad"] = age.where(age >= 16)                                      # implausible ages -> NaN
    for c in CAT_COLS:
        X[c.lower()] = df[c].astype("string").fillna("SIN_DATO")
    X["periodo"] = X["periodo"].astype(str)
    return X


NUM_FEATURES = ["estrato", "fami_educacionpadre", "fami_educacionmadre", "horas_trabajo", "valor_matricula",
                "edad"] + [c.lower() for c in BIN_COLS]
CAT_FEATURES = [c.lower() for c in CAT_COLS]
