#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version EN LIGNE de l'outil CERFA.

Une page web : deux dates + bouton "Go". Au clic, l'appli recupere les factures
Sellsy de la periode, cree les CERFA et renvoie un fichier ZIP a telecharger.

Rien a installer cote client : il ouvre l'adresse dans son navigateur.

Lancement local (test) :  python web_app.py   puis ouvrir http://localhost:8000
En ligne : voir README (section hebergement).
"""

import io
import os
import zipfile
import tempfile
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, request, send_file, render_template_string

import core

app = Flask(__name__)

# Mot de passe de la page. Modifiable via la variable d'environnement APP_PASSWORD.
MOT_DE_PASSE = os.environ.get("APP_PASSWORD", "MB770")

PAGE = """
<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CERFA - MML</title>
<style>
  body{font-family:system-ui,Arial,sans-serif;max-width:560px;margin:40px auto;padding:0 16px;color:#1a2b4a}
  h1{font-size:22px}
  .carte{border:1px solid #d9e1ef;border-radius:12px;padding:24px;background:#fff}
  label{display:block;margin:14px 0 4px;font-weight:600}
  input{width:100%;padding:10px;border:1px solid #c3cfe2;border-radius:8px;font-size:16px;box-sizing:border-box}
  button{margin-top:20px;width:100%;padding:14px;border:0;border-radius:8px;
         background:#1e63d6;color:#fff;font-size:18px;font-weight:700;cursor:pointer}
  button:hover{background:#174fac}
  .info{color:#5a6b8c;font-size:14px;margin-top:16px}
</style></head>
<body>
  <h1>Generation des CERFA</h1>
  <div class="carte">
    <form method="post" action="/generer">
      <label for="d1">Du</label>
      <input type="date" id="d1" name="date_debut" value="{{ defaut }}" required>
      <label for="d2">Au</label>
      <input type="date" id="d2" name="date_fin" value="{{ defaut }}" required>
      <label for="mp">Mot de passe</label>
      <input type="password" id="mp" name="motdepasse" required>
      <button type="submit">Go</button>
    </form>
    <p class="info">Les CERFA des factures de la periode seront prepares
    puis telecharges dans un fichier ZIP. Les cases restent a cocher a la main.</p>
  </div>
</body></html>
"""


@app.get("/")
def accueil():
    hier = (date.today() - timedelta(days=1)).isoformat()
    return render_template_string(PAGE, defaut=hier)


@app.post("/generer")
def generer():
    if request.form.get("motdepasse", "") != MOT_DE_PASSE:
        return ("<p style='font-family:sans-serif;max-width:560px;margin:40px auto'>"
                "Mot de passe incorrect.<br><br><a href='/'>Retour</a></p>"), 403

    d1 = request.form["date_debut"]
    d2 = request.form["date_fin"]
    lignes = []

    with tempfile.TemporaryDirectory() as tmp:
        fichiers = core.generer(d1, d2, log=lignes.append, dossier=tmp)
        if not fichiers:
            return ("<p style='font-family:sans-serif;max-width:560px;margin:40px auto'>"
                    "Aucun CERFA a generer sur cette periode.<br><br>"
                    "<a href='/'>Retour</a></p>")
        # ZIP en memoire
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in fichiers:
                p = Path(p)
                # arborescence AAAA-MM/fichier.pdf conservee dans le zip
                z.write(p, arcname=str(Path(p.parent.name) / p.name))
        buf.seek(0)

    nom = f"CERFA_{d1}_au_{d2}.zip"
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name=nom)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
