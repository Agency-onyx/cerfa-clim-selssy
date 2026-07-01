#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logique metier (independante de l'interface) : recuperation des factures Sellsy
et generation des CERFA dans le dossier de sortie.
"""

from pathlib import Path
import cerfa_fill

BASE = Path(__file__).resolve().parent


def _slug(txt, maxlen=40):
    keep = "-_() "
    s = "".join(c if (c.isalnum() or c in keep) else "-" for c in (txt or ""))
    return s.strip()[:maxlen] or "sans-nom"


def generer(date_debut, date_fin, log=print, dossier=None):
    """Traite la periode et genere les CERFA. `log` affiche l'avancement.
    Si `dossier` est fourni, ecrit dedans ; sinon utilise config.json.
    Retourne la liste des chemins de fichiers generes."""
    import sellsy_client
    cfg = sellsy_client.charger_config()

    if dossier is None:
        dossier = Path(cfg.get("dossier_sortie", "./CERFA"))
        if not dossier.is_absolute():
            dossier = sellsy_client.app_dir() / dossier
    else:
        dossier = Path(dossier)

    log(f"Connexion a Sellsy, factures du {date_debut} au {date_fin}...")
    factures = sellsy_client.factures_a_traiter(cfg, date_debut, date_fin)
    log(f"{len(factures)} facture(s) trouvee(s).")

    fichiers = []
    nb = 0
    for f in factures:
        parts = f["date"].split("/")
        sous = f"{parts[2]}-{parts[1]}" if len(parts) == 3 else "divers"
        cible = dossier / sous
        base_nom = f"{_slug(f['ref'])}_{_slug(f['client'].get('nom', ''))}"

        if cfg.get("generer_1301", True):
            out = cible / f"1301_{base_nom}.pdf"
            cerfa_fill.remplir_1301(f["client"], f["date"], out)
            fichiers.append(out); nb += 1
            log(f"  1301 -> {out.name}")

        if cfg.get("generer_15497", True):
            produits = f["produits_groupe_ext"]
            for i, produit in enumerate(produits, 1):
                suffixe = f"_{i}" if len(produits) > 1 else ""
                out = cible / f"15497_{base_nom}{suffixe}.pdf"
                cerfa_fill.remplir_15497(f["client"], f["date"], produit, out)
                fichiers.append(out); nb += 1
                log(f"  15497 ({produit[:30]}) -> {out.name}")
            if not produits:
                log(f"  (facture {f['ref']} : aucun 'groupe exterieur', pas de 15497)")

    log(f"\nTermine. {nb} document(s) genere(s) dans {dossier}")
    return fichiers
