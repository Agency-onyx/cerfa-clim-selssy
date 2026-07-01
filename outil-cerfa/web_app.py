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

from flask import Flask, request, send_file, render_template_string, make_response

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
  button:disabled{background:#9db6e0;cursor:default}
  .info{color:#5a6b8c;font-size:14px;margin-top:16px}
  #overlay{position:fixed;inset:0;background:rgba(255,255,255,.94);
           display:none;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px}
  #overlay.on{display:flex}
  .spin{width:52px;height:52px;border:5px solid #d7e2f5;border-top-color:#1e63d6;
        border-radius:50%;animation:spin 1s linear infinite;margin-bottom:20px}
  @keyframes spin{to{transform:rotate(360deg)}}
  #overlay h2{font-size:20px;margin:0 0 8px}
  #chrono{color:#5a6b8c;font-size:15px}
  .entete{text-align:center;margin-bottom:8px}
  .entete svg{width:64px;height:64px}
  footer{text-align:center;margin-top:28px;color:#8794ab;font-size:14px}
  footer a{color:#1e63d6;text-decoration:none;font-weight:600}
  footer a:hover{text-decoration:underline}
</style></head>
<body>
  <div class="entete">
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="climatisation">
      <rect x="6" y="12" width="52" height="22" rx="5" fill="#eaf1fc" stroke="#1e63d6" stroke-width="2.5"/>
      <line x1="11" y1="20" x2="53" y2="20" stroke="#1e63d6" stroke-width="2"/>
      <rect x="11" y="26" width="42" height="4" rx="2" fill="#1e63d6"/>
      <path d="M18 41c0 4 5 4 5 8" stroke="#4a90e2" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M31 41c0 4 5 4 5 8" stroke="#4a90e2" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M44 41c0 4 5 4 5 8" stroke="#4a90e2" stroke-width="2.5" stroke-linecap="round"/>
    </svg>
  </div>
  <h1>Generation des CERFA</h1>
  <div class="carte">
    <form id="form" method="post" action="/generer">
      <label for="d1">Du</label>
      <input type="date" id="d1" name="date_debut" value="{{ defaut }}" required>
      <label for="d2">Au</label>
      <input type="date" id="d2" name="date_fin" value="{{ defaut }}" required>
      <label for="mp">Mot de passe</label>
      <input type="password" id="mp" name="motdepasse" required>
      <input type="hidden" id="token" name="token">
      <button id="btn" type="submit">Go</button>
    </form>
    <p class="info">Les CERFA des factures de la periode seront prepares
    puis telecharges dans un fichier ZIP. Les cases restent a cocher a la main.</p>
  </div>

  <div id="overlay">
    <div class="spin"></div>
    <h2>Generation en cours...</h2>
    <div id="chrono">0 s</div>
  </div>

  <footer>
    Cree par <a href="https://onyx-digital.fr" target="_blank" rel="noopener">onyx-digital.fr</a>
  </footer>

  <script>
    var form=document.getElementById('form');
    var overlay=document.getElementById('overlay');
    var chrono=document.getElementById('chrono');
    var btn=document.getElementById('btn');
    form.addEventListener('submit', function(){
      var token=Math.random().toString(36).slice(2)+Date.now();
      document.getElementById('token').value=token;
      overlay.classList.add('on');
      btn.disabled=true;
      var start=Date.now();
      var t=setInterval(function(){
        chrono.textContent=Math.round((Date.now()-start)/1000)+' s';
      },1000);
      // Le serveur pose un cookie 'downloadToken' quand le ZIP part :
      // des qu'on le detecte, le telechargement a commence, on masque l'ecran.
      var poll=setInterval(function(){
        if(document.cookie.indexOf('downloadToken='+token)!==-1){
          clearInterval(poll);clearInterval(t);
          overlay.classList.remove('on');
          btn.disabled=false;
          document.cookie='downloadToken=; max-age=0; path=/';
        }
      },500);
    });
  </script>
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
    resp = make_response(send_file(buf, mimetype="application/zip",
                                   as_attachment=True, download_name=nom))
    # Signale au navigateur que le telechargement demarre (masque l'ecran d'attente).
    token = request.form.get("token", "")
    if token:
        resp.set_cookie("downloadToken", token, max_age=60, path="/")
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
