# Méridien — maquette

Finition haute horlogerie, densité d'information d'une montre connectée. Dessin original.
Maquette seulement : pas encore de paquet WFF.

![Coloris](planche.png)

![Sur la montre](meridien-montre.png)

| Zone | Donnée | Source WFF |
|---|---|---|
| Compteur 9 h | Fréquence cardiaque, aiguille 40–200 + valeur | `[HEART_RATE]` |
| Compteur 3 h | Batterie façon réserve de marche, zone rouge < 20 % | `[BATTERY_PERCENT]` |
| Compteur 6 h | Phase de lune, jour et date | `[MOON_PHASE_POSITION]`, `[DAY_OF_WEEK]`, `[DAY]` |
| Cartouche 12 h | Météo : icône, température, max / min, état | `[WEATHER.*]` (WFF v2) |
| Pourtour | Anneau de progression des pas | `[STEP_PERCENT]` |
| Bas | Pas + ligne de complication (prochain événement) | `[STEP_COUNT]`, complication `LONG_TEXT` |
| Centre | Heures, minutes, trotteuse centrale | `[HOUR_0_11]`, `[MINUTE]`, `[SECOND]` |

Coloris : anthracite / orange, bleu glacier / cyan, panda (cadran blanc, compteurs noirs) /
rouge. AOD : noir pur, aiguilles et index en filet, anneau des pas conservé.

```bash
node concepts/meridien/render.mjs   # Playwright + Chromium, ImageMagick
```

Polices partagées avec `concepts/nocturne/fonts/` (OFL).
