#!/usr/bin/env python3
"""Extrait le jeton de validation Watch Face Push de la sortie de validator-push-cli.

La sortie contient une ligne du type « Validation token: <jeton> ». Échoue (code 1) si la
validation a échoué ou si aucun jeton n'est trouvé : la sortie complète reste dans le journal.
"""
import re
import sys

text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
match = re.search(r"token\s*[:=]\s*(\S{20,})", text, re.IGNORECASE)
if not match:
    sys.exit("Aucun jeton de validation dans la sortie du validateur (voir le journal ci-dessus).")
print(match.group(1).strip())
