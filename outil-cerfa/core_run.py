#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lancement automatique sans interface (pour une tache planifiee quotidienne).

Par defaut : traite les factures de la veille.
Usage optionnel : python core_run.py 2026-04-01 2026-04-30
"""

import sys
from datetime import date, timedelta
from core import generer

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        d1, d2 = sys.argv[1], sys.argv[2]
    else:
        hier = (date.today() - timedelta(days=1)).isoformat()
        d1 = d2 = hier
    generer(d1, d2, print)
