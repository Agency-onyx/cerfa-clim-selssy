#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remplissage des deux CERFA a partir d'une facture Sellsy.

- CERFA 15497-04 : fiche d'intervention fluides frigorigenes.
    Valeurs par defaut (operateur MML, toujours identiques) + valeurs dynamiques
    (client, date de facture, nom du produit). UN CERFA par produit "groupe exterieur".
- CERFA 1301-SD : attestation TVA taux reduit. Identite du client.

Dans les deux cas, les cases a cocher restent VIDES : elles seront cochees a la main.
Les PDF restent MODIFIABLES.

Ce module ne depend pas de Sellsy : il recoit des dictionnaires Python deja prepares.
"""

import re
import unicodedata
from pathlib import Path
import fitz  # PyMuPDF

BASE = Path(__file__).resolve().parent
MODELE_15497 = BASE / "modeles" / "cerfa_15497-04.pdf"
MODELE_1301 = BASE / "modeles" / "cerfa_1301-sd.pdf"

# ---------------------------------------------------------------------------
# Valeurs par defaut de l'operateur (le "bleu" du modele). A ajuster ici si
# les coordonnees de l'entreprise changent.
# ---------------------------------------------------------------------------
OPERATEUR_DEFAUT = {
    "Operateur": "MML CONSEIL MAISON BOREE\n52 RUE D'AGUESSEAU\n92100 BOULOGNE BILLANCOURT\n84492696400025",
    "Attestation_no": "SQ 18115",
    "Sign_Operateur_Nom": "MAXENCE PELUSO",
    "Sign_Operateur_Qualite": "DIRECTEUR",
    "Sign_Operateur_Date": "MP",   # initiales de l'operateur en bas du document
}

MOT_CLE_PRODUIT = "groupe exterieur"  # comparaison sans accents / sans casse


def _sans_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def contient_groupe_exterieur(nom_produit: str) -> bool:
    """True si le nom/description du produit contient 'groupe exterieur'."""
    return MOT_CLE_PRODUIT in _sans_accents(nom_produit)


def _ecrire(modele: Path, valeurs_texte: dict, sortie: Path, fixe: dict = None,
            page1_seulement: bool = False):
    """
    Ecrit dans un PDF a formulaire.
    - valeurs_texte : rempli comme champ de formulaire (reste editable).
    - fixe : {nom_champ: texte} rendu en TEXTE FIXE imprime sur la page,
      centre dans la case du champ (le champ est retire). Utile pour les cases
      trop courtes (dates) qui sont rognees par certains lecteurs PDF.
    - page1_seulement : ne conserve que la premiere page dans le PDF de sortie.
    Les cases a cocher restent vides.
    """
    fixe = fixe or {}
    doc = fitz.open(str(modele))
    for page in doc:
        a_dessiner = []
        for w in list(page.widgets() or []):
            if w.field_name in fixe:
                a_dessiner.append((str(fixe[w.field_name] or ""), fitz.Rect(w.rect)))
                page.delete_widget(w)
            elif w.field_type_string == "Text" and w.field_name in valeurs_texte:
                val = valeurs_texte[w.field_name]
                w.field_value = "" if val is None else str(val)
                w.update()
        for texte, rect in a_dessiner:
            if not texte:
                continue
            fs = 7.0
            larg = fitz.get_text_length(texte, fontname="helv", fontsize=fs)
            x = rect.x0 + max(0, (rect.width - larg) / 2)
            y = rect.y0 + rect.height / 2 + fs * 0.35  # centrage vertical (baseline)
            page.insert_text((x, y), texte, fontsize=fs, fontname="helv")
    if page1_seulement and doc.page_count > 1:
        doc.select([0])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(sortie))
    doc.close()
    return sortie


def _split_date(date_str: str):
    """'29/04/2026' -> ('29','04','2026'). Accepte aussi 2026-04-29."""
    if not date_str:
        return "", "", ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        return m.group(3), m.group(2), m.group(1)
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", date_str)
    if m:
        return m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
    return "", "", ""


# ---------------------------------------------------------------------------
# CERFA 15497-04
# ---------------------------------------------------------------------------
def remplir_15497(client: dict, date_facture: str, nom_produit: str, sortie: Path):
    """
    client        : {"bloc": "Nom\\nAdresse\\nCP Ville"}  (texte deja mis en forme)
    date_facture  : "JJ/MM/AAAA"
    nom_produit   : nom du produit (groupe exterieur) -> reference materiel
    """
    jj, mm, aaaa = _split_date(date_facture)
    valeurs = dict(OPERATEUR_DEFAUT)
    valeurs.update({
        "Detenteur": client.get("bloc", ""),
        "Equipement_ID": nom_produit,
    })
    # La date (cases courtes) est imprimee en texte fixe pour un rendu identique
    # dans tous les lecteurs PDF.
    fixe = {"Controle_Jour": jj, "Controle_Mois": mm, "Controle_Annee": aaaa}
    return _ecrire(MODELE_15497, valeurs, sortie, fixe=fixe)


# ---------------------------------------------------------------------------
# CERFA 1301-SD
# ---------------------------------------------------------------------------
def remplir_1301(client: dict, date_facture: str, sortie: Path):
    """
    client : {"nom","prenom","adresse","cp","commune"}
    """
    valeurs = {
        "a1": client.get("nom", ""),
        "a2": client.get("prenom", ""),
        "a3": client.get("adresse", ""),
        "a5": client.get("cp", ""),
        "a4": client.get("commune", ""),
        # 2e paragraphe (nature des locaux) : PAS d'adresse (consigne client).
        "a11": client.get("commune", ""),   # Fait a
        "a12": date_facture,                 # le ...
    }
    return _ecrire(MODELE_1301, valeurs, sortie, page1_seulement=True)


if __name__ == "__main__":
    # Auto-test rapide avec les donnees reelles observees dans Sellsy.
    client = {
        "bloc": "M Mohand BOUKHEZER\n74 RUE DE ROCHEFORT\n95100 ARGENTEUIL",
        "nom": "BOUKHEZER", "prenom": "Mohand",
        "adresse": "74 RUE DE ROCHEFORT", "cp": "95100", "commune": "ARGENTEUIL",
    }
    remplir_15497(client, "29/04/2026", "Groupe extérieur Multi Split (2MXM50A9)",
                  BASE / "test_15497.pdf")
    remplir_1301(client, "29/04/2026", BASE / "test_1301.pdf")
    print("Tests generes.")
