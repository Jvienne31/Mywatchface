# Règles WFF constatées sur le terrain

Testé avec WFF v2 déclaré (`com.google.wear.watchface.format.version = 2`, minSdk 34), sur
l'émulateur Wear OS 6 (API 36) et sur une Galaxy Watch8 Classic.

## Rendu

| Sujet | Constat | Solution |
|---|---|---|
| Dégradés `LinearGradient` / `RadialGradient` dans `Fill` | **[montre]** non rendus | Aplats, plus PNG RGBA translucides générés en Python (stdlib zlib et struct) : ombrage, reflets, ombre portée |
| `Font > Outline` | **[montre]** non rendu | 12 copies du texte décalées en cercle (rayon d'environ 4,5 px sur 438), couleur du contour, puis le texte. Ombre : une copie noire alpha 110 décalée (3, 6) |
| `Stroke dashIntervals` sur un `Arc` | **[montre]** l'espacement dérive (environ 10° sur un demi-tour) | Une `Line` par graduation ou segment |
| Rectangle penché (parallélogramme) | pas de cisaillement | Traits horizontaux superposés (12 traits de 2 px pour 15 px de haut) en couleur **opaque**, transparence sur le `PartDraw` entier (`alpha`). Des traits translucides font des rayures |
| Texte italique | `Font slant="ITALIC"` fonctionne | Aperçu SVG : `skewX(-12)` |
| Transparence | `alpha` (0-255) sur `PartText`, `PartDraw`, `PartImage`, `Group` | Couleurs « douces » : une couleur de palette avec un alpha |

## Structure et attributs

- **Valeurs entières obligatoires** pour x, y, width et height des `PartText`, `PartImage`,
  `PartDraw`, `Group` et `ComplicationSlot`. Le validateur refuse `38.44`.
- **Coordonnées des enfants d'un `Group`** : relatives au Group.
- **Un `ListOption` n'a qu'un enfant** : l'envelopper dans un `Group`.
- **`Condition`** : `<Expressions><Expression name="e"><![CDATA[…]]></Expression></Expressions>`,
  puis `<Compare expression="e">…</Compare>` et `<Default>…</Default>`. Les enfants
  autorisés sont `Group`, `Condition` ou horloges : envelopper les `PartText` dans un
  `Group`.
- **`Group`** : `pivotX` et `pivotY` sont **normalisés** (0-1) dans la boîte du Group ;
  `scaleX` et `scaleY` sont acceptés ; `angle` fait tourner autour du pivot.
- **Échappement** : `&gt;` dans les attributs ; `CDATA` dans `<Expression>`.

## Couleurs configurables

- **Limite** : `ColorConfiguration > ColorOption colors="…"` porte au plus **5** couleurs.
  Référence : `[CONFIGURATION.palette.0]` … `.4`.
- **Dégradés** : on ne peut pas mélanger des références de configuration dans une liste de
  couleurs. Utiliser `[CONFIGURATION.x]` en entier ou des aplats.
- **Couleurs dérivées** (texte doux, pistes de jauge) : couleur de la palette et `alpha`.
- **Encres par zone** : le générateur choisit l'encre claire ou sombre selon le fond, puis
  vérifie un contraste d'au moins 3,5 pour toutes les palettes. Si une palette échoue, ajuster
  la couleur de bande (le test s'exécute à chaque génération).
- **Variation subtile** (par exemple entre heures et minutes) : seconde copie du texte dans
  l'accent, avec un alpha d'environ 55.

## Masques et loupe

- **Masque** : `renderMode="MASK"` sur un enfant (`Group` ou `PartDraw`) découpe les enfants
  `SOURCE` (par défaut) du **même** parent. L'ordre ne compte pas. **[montre]** Fonctionne,
  même avec un Group tourné comme masque.
- **Loupe** (dôme) : un `Group scaleX=scaleY=1.2` centré sur le dôme, un
  `ComplicationSlot scaleX/scaleY=1.2`, et des PNG de verre (reflet, croissant, filet) et
  d'ombre.
  - Mettre un **fond uni** sous la loupe : un fond agrandi (bandes) laisse un croissant de la
    zone voisine au bord.
  - Un patch dans un emplacement agrandi doit avoir le rayon du dôme divisé par 1,2.

## ComplicationSlot

- `BoundingBox` ou `BoundingOval` est obligatoire, ainsi qu'au moins une `Complication`.
  `DefaultProviderPolicy` est facultatif, mais s'il est présent il exige un
  `defaultSystemProviderType`.
- **[montre]** `Complication type="EMPTY"` **n'est pas dessiné** quand aucune source n'est
  choisie. Schéma qui marche :
  1. dessiner la donnée par défaut (tags WFF) dans un `Group` **sous** l'emplacement ;
  2. dans chaque `Complication` non vide, redessiner d'abord le fond à la forme de
     l'emplacement (rectangle masqué ou disque uni), puis la donnée de la source ;
  3. laisser `EMPTY` vide.
- **Accepter tous les types**, sinon les sources dont aucun type n'est accepté sont **absentes
  du sélecteur**.
- **Données d'une source** :
  - texte : `[COMPLICATION.TEXT]` et `[COMPLICATION.TITLE]` ;
  - icône : `[COMPLICATION.MONOCHROMATIC_IMAGE]` avec `tintColor`, et
    `[COMPLICATION.SMALL_IMAGE]`, `[COMPLICATION.PHOTO_IMAGE]` ;
  - progression : `([COMPLICATION.RANGED_VALUE_VALUE] - [COMPLICATION.RANGED_VALUE_MIN]) /
    ([COMPLICATION.RANGED_VALUE_MAX] - [COMPLICATION.RANGED_VALUE_MIN])`, ou
    `[COMPLICATION.GOAL_PROGRESS_VALUE] / [COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]`.
- **Largeur du texte** : prévoir large (environ 80 px pour une valeur de dôme), sinon
  « 6h 29m » est tronqué en « 6h 29m… ».
- **Sources choisies par erreur** : une source de pas de Wear OS peut n'envoyer que du texte,
  sans objectif ni icône. L'expliquer à l'utilisateur plutôt que d'y voir un bug.

## Toucher

- `<Launch target="…"/>` dans un `Group` dont x, y, w, h forment la zone sensible. Un Group
  plein écran rend tout l'écran sensible.
- **Raccourcis système** : `CALENDAR`, `BATTERY_STATUS`, `HEALTH_HEART_RATE`, `ALARM`,
  `MESSAGE`, `MUSIC_PLAYER`, `PHONE`, `SETTINGS`.
- **Nom de paquet**, par exemple `com.samsung.android.watch.weather` (Météo Samsung) ou
  `com.samsung.android.wear.shealth` (Samsung Health montre). On peut aussi donner
  `paquet/activité` ou un lien profond `app://…`.
- **[montre]** Fonctionne sous un emplacement vide (le Group de la donnée par défaut est sous
  le `ComplicationSlot`).

## Tags utiles (v2)

- **Heure** : `[HOUR_0_23_Z]`, `[HOUR_1_12_Z]`, avec `[IS_24_HOUR_MODE]` pour choisir ;
  `[MINUTE_Z]` ; `[SECOND]`.
- **Date** : `[DAY_Z]`, `[MONTH_S]` (avec `<Upper>`), `[DAY_OF_WEEK_F]`.
- **Santé et batterie** :
  - `[HEART_RATE]`, en testant `> 0` et en affichant « -- » sinon ;
  - `[BATTERY_PERCENT]` ;
  - `[STEP_COUNT]`, `[STEP_PERCENT]`.
- **Météo** :
  - `[WEATHER.IS_AVAILABLE]`, `[WEATHER.TEMPERATURE]` (gabarit `%s°`),
    `[WEATHER.CHANCE_OF_PRECIPITATION]`, `[WEATHER.UV_INDEX]` ;
  - `[WEATHER.CONDITION]` : 1 et 8 soleil, 14 partiellement nuageux, 4, 6 et 12 pluie, 5, 7,
    10 et 11 neige, 9 orage, 3 et 13 brouillard, sinon nuage.
- **Absents du format** : calories, distance, scores. Il faut une complication pour les
  afficher.

## AOD

- Mesure : `convert aod.png -alpha off -colorspace gray -threshold 8% -format "%[fx:mean*100]" info:`.
  Doit rester sous 15 %. Prisme fait environ 6 %.
- Masquer en AOD : `<Variant mode="AMBIENT" target="alpha" value="0"/>`.
- N'afficher qu'en AOD : `alpha="0"` plus `Variant` ambient avec `value="255"`.
- Chiffres fins (police Light) sur noir ; l'accent sur les minutes reste lisible.
