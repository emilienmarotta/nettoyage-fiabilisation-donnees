"""Vérifie qu'exécuter ingestion + nettoyage deux fois sur le même fichier
source donne un état final strictement identique dans `clean_staging.*`
(specs/06-orchestration.md). Nécessite Postgres démarré
(`docker compose up -d`) : ignoré plutôt que de faire échouer `pytest` dans
un environnement sans base.
"""
from pathlib import Path

import psycopg2
import pytest

from generator import config as generator_config
from generator.main import run as generer
from pipeline.clean.run import nettoyer
from pipeline.db import get_connection
from pipeline.ingest import ingerer


def _db_disponible() -> bool:
    try:
        get_connection().close()
        return True
    except psycopg2.OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _db_disponible(), reason="Postgres non disponible (lancer `docker compose up -d`)"
)


def _executer_une_passe(fichier: Path) -> None:
    conn = get_connection()
    try:
        ingerer(fichier, conn)
    finally:
        conn.close()

    conn = get_connection()
    try:
        nettoyer(conn, fichier.name)
    finally:
        conn.close()


def _requeter(sql: str, params: tuple) -> list[tuple]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return sorted(cur.fetchall())
    finally:
        conn.close()


def _capturer_etat(source_fichier: str) -> dict[str, list[tuple]]:
    return {
        "clients": _requeter(
            "SELECT ligne_origine, client_id, code_client, nom_entreprise, contact_nom, "
            "email, telephone, adresse, code_postal, ville, region, siret, segment, "
            "date_creation FROM clean_staging.clients WHERE source_fichier = %s",
            (source_fichier,),
        ),
        "produits": _requeter(
            "SELECT ligne_origine, produit_id, code_produit, nom_produit, categorie, "
            "prix_unitaire, unite, fournisseur FROM clean_staging.produits "
            "WHERE source_fichier = %s",
            (source_fichier,),
        ),
        "commandes": _requeter(
            "SELECT ligne_origine, commande_id, client_id, produit_id, quantite, "
            "prix_unitaire_commande, date_commande, date_livraison, statut "
            "FROM clean_staging.commandes WHERE source_fichier = %s",
            (source_fichier,),
        ),
        "correction_log": _requeter(
            "SELECT source_onglet, ligne_origine, table_cible, colonne, valeur_avant, "
            "valeur_apres, regle_appliquee FROM clean_staging.correction_log "
            "WHERE source_fichier = %s",
            (source_fichier,),
        ),
        "quarantine": _requeter(
            "SELECT source_onglet, ligne_origine, table_cible, donnees_brutes, motif_rejet "
            "FROM clean_staging.quarantine WHERE source_fichier = %s",
            (source_fichier,),
        ),
    }


def test_pipeline_idempotent(tmp_path: Path):
    # Même graine/taux que `make generate` : le fichier généré ici est
    # strictement identique au fichier de démo versionné en local, donc
    # rejouer ce test laisse `clean_staging.*` dans l'état où `make run`
    # l'aurait déjà laissé (pas d'effet de bord sur les données de démo).
    generer(
        seed=generator_config.SEED,
        taux_defauts=generator_config.TAUX_DEFAUTS_DEFAUT,
        data_dir=tmp_path,
    )
    fichier = tmp_path / "clients_commandes_brut.xlsx"

    _executer_une_passe(fichier)
    etat_premiere_passe = _capturer_etat(fichier.name)

    _executer_une_passe(fichier)
    etat_seconde_passe = _capturer_etat(fichier.name)

    assert etat_premiere_passe == etat_seconde_passe
    # Sanity check : le test ne doit pas comparer des listes vides.
    assert len(etat_premiere_passe["clients"]) > 0
    assert len(etat_premiere_passe["commandes"]) > 0
