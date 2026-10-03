# Chaîne d'outils : maquette, génération, validation, CI, test

## Maquettes (choix du style)

- **Rendu.** Écrire la maquette en SVG depuis Node, puis l'exporter en PNG avec Playwright
  (Chromium). Le conteneur fournit Chromium dans `/opt/pw-browsers` et les modules Node dans
  `/opt/node-tools/node_modules` : faire un lien temporaire `node_modules` vers ce dossier, à
  supprimer avant le commit.
- **Polices.** Charger la page depuis un **fichier** (`writeFileSync` puis
  `page.goto(file://…)`). Avec `setContent`, les polices locales ne se chargent pas.
- **Planches de comparaison.** Mettre côte à côte la version actuelle, A et B, avec un titre
  et un sous-titre par variante. L'utilisateur choisit vite.
- **Vue « au poignet ».** Composer la maquette sur un fond de montre, par exemple une image
  640 × 820 dont l'écran est à +101+191.
- **Polices du paquet.**
  1. Récupérer le woff2 avec `npm pack @fontsource/<police>`.
  2. Le convertir en ttf : `python -c "from fontTools.ttLib import TTFont; f=TTFont('x.woff2'); f.flavor=None; f.save('x.ttf')"`
     (paquets pip `fonttools` et `brotli`).
  3. Ressource `res/font/nom_graisse.ttf`, référencée par `Font family="nom_graisse"`.
  4. N'utiliser que des polices OFL, et copier leur licence.

## Générateur (`scripts/wff.py`)

- **Principe.** Chaque primitive (`text`, `arc`, `line`, `rect`, `rrect`, `circle`, `image`,
  `group_open`/`group_close`, `draw_open`/`draw_close`, `condition`, `list_config`) écrit le
  XML WFF **et** son équivalent SVG.
- **Le module appelant renseigne** :
  - `wff.RES` (dossier `res/`) ;
  - `wff.DEFAULT_COLORS` (`[CONFIGURATION.x.i]` vers une couleur, pour l'aperçu) ;
  - `wff.FONTS` (ressource vers une famille CSS).
- **Visibilité de l'aperçu** : `O.mode_stack` gère `both`, `normal`, `ambient` et `none`. Pour
  le XML seul, utiliser `none`.
- **Coordonnées** : absolues dans la toile (438 px sur la Watch8 Classic 46 mm, à vérifier
  pour chaque modèle). `rel()` et `_box()` les convertissent en coordonnées relatives et
  **entières**.
- **PNG d'ombrage et de verre** : en Python stdlib (`zlib`, `struct`), avec une fonction
  pixel → RGBA et une composition « over ».
- **Rendu de l'aperçu** : le script `render-preview.mjs` produit `preview.png` (embarqué dans
  le paquet) et l'aperçu AOD (contrôle).

## Validation

- **Validateur.** Compiler le validateur du dépôt `google/watchface`, puis
  `validate.sh <version> watchface.xml`. Il doit afficher `PASSED`.
- **Erreurs typiques** :

  | Message | Cause |
  |---|---|
  | `'38.44' is not a valid value for 'integer'` | x, y, w ou h d'un Part non arrondi |
  | `maxLength '5' … userStyleColorOptionType` | `ColorOption` avec plus de 5 couleurs |

- **AOD** : `convert aod.png -alpha off -colorspace gray -threshold 8% -format "%[fx:mean*100]" info:`,
  doit rester sous 15.
- **Non-régression visuelle** : `compare -metric AE avant.png apres.png null:` doit donner 0
  quand on ne change que de la structure (toucher, groupes).

## CI (GitHub Actions)

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-java@v4   # temurin 17
  with: { distribution: temurin, java-version: "17" }
# pas d'action setup-android : le SDK est déjà sur ubuntu-latest
- run: chmod +x gradlew && ./gradlew --no-daemon :module:assembleDebug
- uses: actions/upload-artifact@v4   # le lien de l'artefact sert à l'utilisateur
```

- Un workflow par module, déclenché par `paths`.
- Suivi : `gh run list` / `gh run watch --exit-status` ; journaux par MCP `get_job_logs`.
- Le conteneur n'a pas accès à Google Maven : **toute** compilation Android passe par la CI.

## Test sur la montre

- **Installation** : Wear Installer 2 (téléphone vers montre, en Wi-Fi), ou
  `adb -s <montre> install -r x.apk`.
- **Mise à jour** : même clé, donc pas besoin de désinstaller.
  `INSTALL_FAILED_UPDATE_INCOMPATIBLE` signifie une clé différente : désinstaller une fois.
- **Choisir la complication sur la montre** plutôt que dans l'appli Galaxy Wearable, dont les
  listes sont parfois incomplètes ou tardives.
- **Émulateur** : profil matériel et skin Watch8 Classic possibles. Samsung Health n'y est pas,
  et le comportement des emplacements peut différer : valider sur la montre.
