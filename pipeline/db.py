"""Connexion Postgres et chargement minimal de `.env` (sans dépendance
externe), partagés par les étapes du pipeline."""

import os
from pathlib import Path

import psycopg2


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for ligne in path.read_text().splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        os.environ.setdefault(cle.strip(), valeur.strip())


def get_connection():
    load_dotenv()
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5434"),
        dbname=os.environ.get("POSTGRES_DB", "nettoyage_fiabilisation"),
        user=os.environ.get("POSTGRES_USER", "pipeline_user"),
        password=os.environ.get("POSTGRES_PASSWORD", "change_me"),
    )
