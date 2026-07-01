#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application CERFA - MML.

Fenetre simple : on choisit une periode (par defaut : hier), on clique
"Generer les CERFA". L'outil recupere les factures Sellsy de la periode,
remplit les CERFA et les depose dans le dossier de sortie, ranges par mois.

Regles :
- Un CERFA 15497 par produit "groupe exterieur" de chaque facture.
- Un CERFA 1301 (attestation TVA) par facture.
- Cases a cocher laissees vides, PDF modifiables.

Lancement : double-clic sur l'application (ou : python app.py).
"""

import threading
import traceback
from datetime import date, timedelta

import tkinter as tk
from tkinter import ttk

from core import generer


# --------------------------------------------------------------------------- UI
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CERFA - MML")
        self.geometry("560x460")
        self.resizable(False, False)

        hier = date.today() - timedelta(days=1)
        pad = {"padx": 10, "pady": 6}

        ttk.Label(self, text="Generation automatique des CERFA",
                  font=("", 14, "bold")).pack(**pad)

        cadre = ttk.Frame(self); cadre.pack(**pad)
        ttk.Label(cadre, text="Du (AAAA-MM-JJ) :").grid(row=0, column=0, sticky="e")
        self.e_debut = ttk.Entry(cadre, width=14)
        self.e_debut.insert(0, hier.isoformat()); self.e_debut.grid(row=0, column=1, padx=6)
        ttk.Label(cadre, text="Au (AAAA-MM-JJ) :").grid(row=1, column=0, sticky="e")
        self.e_fin = ttk.Entry(cadre, width=14)
        self.e_fin.insert(0, hier.isoformat()); self.e_fin.grid(row=1, column=1, padx=6)

        self.bouton = ttk.Button(self, text="Go", command=self.lancer)
        self.bouton.pack(**pad)

        self.journal = tk.Text(self, height=15, width=66, state="disabled")
        self.journal.pack(**pad)

    def log(self, msg):
        self.journal.configure(state="normal")
        self.journal.insert("end", msg + "\n")
        self.journal.see("end")
        self.journal.configure(state="disabled")
        self.update_idletasks()

    def lancer(self):
        self.bouton.configure(state="disabled")
        self.journal.configure(state="normal"); self.journal.delete("1.0", "end")
        self.journal.configure(state="disabled")

        def worker():
            try:
                generer(self.e_debut.get().strip(), self.e_fin.get().strip(), self.log)
            except FileNotFoundError:
                self.log("ERREUR : config.json introuvable. Copier config.example.json "
                         "en config.json et y coller les codes Sellsy.")
            except Exception:
                self.log("ERREUR :\n" + traceback.format_exc())
            finally:
                self.bouton.configure(state="normal")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
