#!/bin/sh
# Regenera todo (datos limpios, figuras, resultados, informe PDF y Word). Ejecutar desde la raiz del repo.
set -e
cd src
mkdir -p ../reports_tmp ../reports/figures_es
for f in 01_clean 02_eda 03_mining 03b_mining_extra 04_ml 06_cost_estimate 08_extra_checks 07_diagrams_es; do python3 $f.py; done
python3 es_figures.py && python3 _es_02_eda.py && python3 _es_03_mining.py && rm -f _es_*.py && rm -rf ../reports_tmp
python3 10_build_report_es.py && python3 export_es_items.py
cd .. && NODE_PATH=$(npm root -g) node src/build_docx_es.js
