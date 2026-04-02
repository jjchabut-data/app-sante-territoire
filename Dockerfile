FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# libapp (dépendance de l'API)
COPY src/libapp ./src/libapp

# Point d'entrée API
COPY api/main.py .

# Données
COPY data/final/mart_sante_comm_indic.parquet ./data/final/mart_sante_comm_indic.parquet
COPY data/final/mart_apl_historique.parquet   ./data/final/mart_apl_historique.parquet
COPY api/data/mart_ref_territoires.parquet    ./data/mart_ref_territoires.parquet

ENV PORT=8080
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
