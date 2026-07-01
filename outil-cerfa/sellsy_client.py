#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Client Sellsy (API v1, OAuth1) : recupere les factures d'une periode, leurs
lignes produit et le client associe.

Dependances : requests, requests_oauthlib

Les 4 codes d'acces Sellsy sont lus depuis config.json (voir config.example.json).

NOTE : la structure exacte des reponses Sellsy peut varier legerement selon le
compte. Le parsing ci-dessous est robuste (plusieurs cles testees) et pourra
etre ajuste au premier vrai test avec les tokens du client.
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from requests_oauthlib import OAuth1

CIVIL = {"man": "M", "woman": "Mme", "miss": "Mme", "": ""}


def _strip_html(html: str) -> str:
    """Enleve les balises HTML et normalise les espaces."""
    txt = re.sub(r"<[^>]+>", " ", html or "")
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", txt).strip()


def _nom_produit(row: dict) -> str:
    """Nom lisible du produit = titre de la description (champ notes),
    sinon le code (champ name)."""
    desc = _strip_html(row.get("notes", ""))
    if desc:
        titre = re.split(r"[:.\-–]", desc, 1)[0].strip()
        return titre or desc
    return (row.get("name") or "").strip()


def _texte_detection(row: dict) -> str:
    """Texte dans lequel on cherche 'groupe exterieur' (code + description)."""
    return f"{row.get('name','')} {_strip_html(row.get('notes',''))}"

import sys

API_URL = "https://apifeed.sellsy.com/0/"
BASE = Path(__file__).resolve().parent


def app_dir() -> Path:
    """Dossier des fichiers utilisateur (config.json, sortie).
    - En .exe/.app : le dossier qui contient l'executable.
    - En script : le dossier du projet."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return BASE


def charger_config():
    """Charge la configuration.
    Priorite au fichier config.json ; a defaut, variables d'environnement
    (pratique pour l'hebergement en ligne, sans fichier de secrets)."""
    import os
    fichier = app_dir() / "config.json"
    if fichier.exists():
        return json.loads(fichier.read_text(encoding="utf-8"))
    if os.environ.get("SELLSY_CONSUMER_TOKEN"):
        return {
            "sellsy": {
                "consumer_token": os.environ["SELLSY_CONSUMER_TOKEN"],
                "consumer_secret": os.environ["SELLSY_CONSUMER_SECRET"],
                "user_token": os.environ["SELLSY_USER_TOKEN"],
                "user_secret": os.environ["SELLSY_USER_SECRET"],
            },
            "dossier_sortie": os.environ.get("DOSSIER_SORTIE", "./CERFA"),
            "generer_1301": os.environ.get("GENERER_1301", "1") != "0",
            "generer_15497": os.environ.get("GENERER_15497", "1") != "0",
        }
    raise FileNotFoundError(
        "Aucune configuration : creer config.json ou definir les variables "
        "d'environnement SELLSY_CONSUMER_TOKEN, SELLSY_CONSUMER_SECRET, "
        "SELLSY_USER_TOKEN, SELLSY_USER_SECRET."
    )


def _auth(cfg):
    s = cfg["sellsy"]
    return OAuth1(
        s["consumer_token"],
        client_secret=s["consumer_secret"],
        resource_owner_key=s["user_token"],
        resource_owner_secret=s["user_secret"],
        signature_type="auth_header",
    )


def _appel(cfg, method, params=None):
    """Appel generique de l'API Sellsy v1."""
    do_in = {"method": method, "params": params or {}}
    data = {"request": 1, "io_mode": "json", "do_in": json.dumps(do_in)}
    r = requests.post(API_URL, data=data, auth=_auth(cfg), timeout=40)
    r.raise_for_status()
    out = r.json()
    if out.get("status") != "success":
        raise RuntimeError(f"Sellsy a repondu une erreur : {out.get('error')}")
    return out.get("response", {})


def _ts(date_str, fin=False):
    """'2026-04-29' -> timestamp unix (debut ou fin de journee)."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    if fin:
        d = d.replace(hour=23, minute=59, second=59)
    return int(time.mktime(d.timetuple()))


def lister_factures(cfg, date_debut, date_fin):
    """
    Retourne les factures dont la date de CREATION (champ `created`) est comprise
    entre date_debut et date_fin (AAAA-MM-JJ), bornes incluses.

    Le filtre serveur de Sellsy n'etant pas fiable, on parcourt la liste triee
    par date de creation decroissante et on filtre cote client, avec arret des
    qu'on passe sous la date de debut.
    """
    factures = []
    page = 1
    while True:
        params = {
            "doctype": "invoice",
            "order": {"order": "created", "direction": "desc"},
            "pagination": {"nbperpage": 100, "pagenum": page},
        }
        resp = _appel(cfg, "Document.getList", params)
        result = resp.get("result", resp)
        items = list(result.values()) if isinstance(result, dict) else (result or [])
        if not items:
            break

        trop_vieux = False
        for it in items:
            d = (it.get("created") or "")[:10]   # 'AAAA-MM-JJ'
            if not d:
                continue
            if d < date_debut:
                trop_vieux = True
                continue
            if d > date_fin:
                continue
            factures.append(it)

        infos = resp.get("infos", {}) or {}
        nbpages = int(infos.get("nbpages", page))
        if trop_vieux or page >= nbpages:
            break
        page += 1

    return factures


def detail_facture(cfg, docid):
    """Detail complet d'une facture (lignes + adresse tierce)."""
    return _appel(cfg, "Document.getOne", {"doctype": "invoice", "docid": docid})


def detail_client(cfg, clientid):
    """Fiche client (contact, corporation, adresse)."""
    return _appel(cfg, "Client.getOne", {"clientid": clientid})


def _rows(detail):
    """Liste des lignes produit (dicts) d'une facture."""
    rows = (detail.get("map", {}) or {}).get("rows", {})
    items = list(rows.values()) if isinstance(rows, dict) else (rows or [])
    return [r for r in items if isinstance(r, dict) and r.get("type") == "item"]


CIVILITES = {"m", "m.", "mr", "mr.", "mme", "mme.", "mlle", "melle", "mlle."}


def _split_nom(nom_complet):
    """'M Mohand BOUKHEZER' -> (prenom='Mohand', nom='BOUKHEZER')."""
    tokens = (nom_complet or "").split()
    if tokens and tokens[0].lower() in CIVILITES:
        tokens = tokens[1:]
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return "", tokens[0]
    return tokens[0], " ".join(tokens[1:])


def _client_infos(detail):
    """
    Construit les infos client A PARTIR DE LA FACTURE UNIQUEMENT.
    (Toutes les donnees necessaires sont deja dans Document.getOne : plus besoin
    d'un appel Client.getOne par facture, ce qui evitait les timeouts.)
    """
    thirdadr = detail.get("thirdAddress", {}) or {}
    rue = thirdadr.get("part1", "")
    part2 = thirdadr.get("part2", "")
    cp = thirdadr.get("zip", "")
    ville = thirdadr.get("town", "")
    if not ville:
        # extraction depuis "95100 Argenteuil". Selon les clients, les elements
        # de partsToDisplay sont des dicts {"txt": ...} OU de simples chaines.
        for p in thirdadr.get("partsToDisplay", []):
            txt = p.get("txt", "") if isinstance(p, dict) else str(p)
            m = re.match(r"\s*\d{4,5}\s+(.+)", txt)
            if m:
                ville = m.group(1).strip()

    rue_complete = " ".join(x for x in [rue, part2] if x).strip()
    intitule = detail.get("thirdName") or detail.get("contactName") or ""
    siret = detail.get("thirdSiret", "")

    # nom / prenom pour le 1301
    if detail.get("thirdType") == "corporation":
        prenom, nom = "", (intitule or "").strip()
    else:
        prenom, nom = _split_nom(detail.get("contactName") or intitule)

    lignes_bloc = [intitule, rue_complete, f"{cp} {ville}".strip()]
    if siret:
        lignes_bloc.append(f"SIRET {siret}")
    bloc = "\n".join(x for x in lignes_bloc if x)

    return {
        "bloc": bloc,
        "nom": nom, "prenom": prenom,
        "adresse": rue_complete, "cp": cp, "commune": ville,
    }


def factures_a_traiter(cfg, date_debut, date_fin, log=None):
    """
    Pour chaque facture de la periode, retourne :
      { ref, date (JJ/MM/AAAA), client{...}, produits_groupe_ext:[noms] }
    Une facture au format inattendu est ignoree (et signalee) sans faire
    echouer tout le lot.
    """
    from cerfa_fill import contient_groupe_exterieur

    resultats = []
    for f in lister_factures(cfg, date_debut, date_fin):
        docid = f.get("id") or f.get("docid")
        if not docid:
            continue
        ref = f.get("ident") or str(docid)
        try:
            detail = detail_facture(cfg, docid)

            # Detection sur le NOM du produit (titre), pas la description complete :
            # evite de capter un "cache clim" dont la description mentionne le groupe exterieur.
            produits_ge = [_nom_produit(r) for r in _rows(detail)
                           if contient_groupe_exterieur(_nom_produit(r))]

            date_aff = detail.get("displayedDate") or f.get("displayedDate") or ""
            if str(date_aff).isdigit():
                date_aff = datetime.fromtimestamp(int(date_aff)).strftime("%d/%m/%Y")

            resultats.append({
                "ref": detail.get("ident") or ref,
                "date": date_aff,
                "client": _client_infos(detail),
                "produits_groupe_ext": produits_ge,
            })
        except Exception as e:
            if log:
                log(f"  ATTENTION : facture {ref} ignoree ({type(e).__name__}: {e})")
    return resultats
