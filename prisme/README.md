# Prisme — cadran Watch Face Format

Cadran numérique pour Galaxy Watch8 Classic (Wear OS 5+, WFF v2, sans code).
Maquette validée : `concepts/prisme/` (version « 2 dômes », palette Lagune).

- Heures et minutes sur deux lignes, en italique : chiffres clairs avec contour sombre et
  ombre, lisibles sur toutes les bandes ; minutes légèrement teintées de la couleur d'accent.
- 4 bandes diagonales. 18 palettes sont proposées dans *Personnaliser > Palette* : Lagune
  (par défaut), Volcan, Ardoise, Moka, Sauge, Lavande, Cerise, Cobalt, Olive, Dune, Néon,
  Graphite, Forêt, Pêche, Beurre, Bordeaux, Abysse, Aurore.
- 7 emplacements de données. Chacun montre une donnée intégrée tant qu'il est vide. Une
  autre source peut lui être attribuée dans *Personnaliser > Complications*.

  | # | Emplacement | Donnée intégrée |
  |---|---|---|
  | 1 | haut gauche | date : jour du mois, mois, jour de la semaine |
  | 2 | gauche | météo : pictogramme et température |
  | 3 | dôme bas gauche | indice UV, en jauge |
  | 4 | dôme haut droite | probabilité de pluie, en jauge |
  | 5 | droite | fréquence cardiaque |
  | 6 | droite | batterie |
  | 7 | bas | pas, avec une barre de 10 segments et l'objectif en % |

  Il n'existe pas de balise « calories » dans le format. Pour afficher les calories,
  attribuez la complication *Samsung Health > Calories* à l'un des dômes.
- Les 2 dômes font un effet de loupe : le fond et le contenu sont agrandis 1,2 fois, et
  un verre ajoute reflet, croissant de lumière et ombre portée.
- Mode AOD : fond noir, chiffres fins, minutes en accent. Environ 6 % de pixels allumés
  (la limite est 15 %).

## Construire

```sh
node prisme/tools/icons.mjs            # pictogrammes (une fois)
python3 prisme/tools/generate.py       # watchface.xml, PNG de verre et d'ombrage, aperçus SVG
node prisme/tools/render-preview.mjs   # preview.png
./gradlew :prisme:assembleDebug        # ou l'action GitHub « APK Prisme »
```

`src/main/res/raw/watchface.xml` est généré : ne pas l'éditer à la main.

## Choix techniques

Ces choix tiennent compte des limites constatées sur l'émulateur avec Race.

- Pas de dégradé (non rendu). Le volume vient de PNG translucides : `bands_shade`,
  `dome_glass`, `dome_shadow`.
- Contour des chiffres : l'élément `Outline` n'est pas rendu sur la montre. Chaque chiffre
  est donc dessiné 12 fois, décalé en cercle de 4,5 px dans la couleur sombre, puis par-dessus
  dans la couleur claire. Une copie noire translucide décalée fait l'ombre.
- Un `ColorOption` porte au plus 5 couleurs : les 4 bandes et l'accent. Les autres
  couleurs en découlent.
  - Données : encre claire sur les bandes 0-1, sombre sur les bandes 2-3. Le générateur
    vérifie un contraste d'au moins 3,5 pour chaque palette.
  - Textes « doux » et pistes des jauges : une couleur de la palette avec de la
    transparence.
- Pourcentages : la valeur et le « % » sont deux textes séparés. Le format n'a pas de
  `%%` fiable dans les gabarits.
- Barre de pas : chaque segment est un parallélogramme fait de 12 traits horizontaux. Le
  format ne permet pas d'incliner un rectangle sans le tourner.

Polices : Big Shoulders Display et Barlow Condensed, sous licence SIL OFL (voir `licences/`).
