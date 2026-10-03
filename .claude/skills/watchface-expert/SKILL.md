---
name: watchface-expert
description: Expert en cadrans Galaxy Watch / Wear OS en Watch Face Format (WFF) et en applis compagnons (complications, Samsung Health, Health Services). À utiliser pour concevoir, générer, valider, déboguer ou publier un cadran ou une appli de complications dans ce dépôt (prisme/, race/, energyscore-*/), et pour toute question « peut-on afficher telle donnée sur un cadran ».
---

# Expert cadrans Wear OS (WFF) — retours d'expérience du projet Prisme

Savoir acquis en construisant Prisme (`prisme/`), Race (`race/`) et Santé Sync
(`energyscore-phone/`, `energyscore-watch/`), testés sur l'émulateur Wear OS 6 (API 36) et une
Galaxy Watch8 Classic. Les règles marquées **[montre]** sont des constats sur l'appareil réel
ou sur l'émulateur. Elles priment sur la documentation.

## 1. Méthode de travail

1. **Maquette avant code.** Le style se valide en images, pas en APK.
   - L'utilisateur juge sur des rendus côte à côte : version actuelle, puis A, puis B.
   - Les maquettes sont des pages SVG rendues avec Playwright (`concepts/*/render.mjs`).
   - Montrer aussi le cadran posé sur une montre : skin `race/emulator/skin-galaxy-watch8-classic`
     (fond 640 × 820, écran à +101+191).
   - Polices : woff2 via `npm pack @fontsource/…`, converties en ttf avec fontTools pour le
     paquet. Ne garder que des polices OFL et copier leur licence dans `licences/`.
   - Avec Playwright, charger les pages depuis un fichier (`page.goto(file://…)`), sinon les
     polices locales ne se chargent pas (`setContent`).
2. **Ne jamais écrire le XML à la main.** Un générateur Python produit en même temps le XML
   WFF et un aperçu SVG.
   - Voir `prisme/tools/wff.py`, primitives miroirs : `text`, `arc`, `rect`, `group_open`,
     `image`…
   - Coordonnées absolues dans une toile de 438 px ; `rel()` les convertit en coordonnées
     relatives aux Group.
3. **Valider le XML** avec le validateur officiel `google/watchface` (version 2 du format)
   avant tout push.
4. **Construire en CI.** Google Maven est bloqué dans le conteneur, donc on construit dans
   GitHub Actions (`.github/workflows/build-*.yml`, Java 17, sans action setup-android).
   - L'utilisateur télécharge l'artefact et l'installe avec Wear Installer ou `adb install -r`.
   - Les journaux de CI ne sont pas téléchargeables depuis le conteneur : passer par l'outil
     MCP `get_job_logs`.
5. **Clé debug versionnée** (`*/debug.keystore`) : les mises à jour s'installent sans
   désinstaller. Une erreur INSTALL_FAILED_UPDATE_INCOMPATIBLE se règle par une seule
   désinstallation.
6. **Toujours vérifier l'AOD** : moins de 15 % de pixels allumés. Mesure :
   `convert aod.png -alpha off -colorspace gray -threshold 8% -format "%[fx:mean*100]" info:`

## 2. Règles WFF apprises

### Rendu

- **[montre]** Les dégradés (`LinearGradient`, `RadialGradient` dans `Fill`) ne sont pas
  rendus. Utiliser des aplats plus des PNG translucides pour l'ombrage, les reflets et les
  ombres.
- **[montre]** `dashIntervals` dérive le long des arcs. Dessiner une `Line` par graduation ou
  segment.
- **[montre]** `Font > Outline` n'est pas rendu.
  - Contour : 12 copies du texte décalées en cercle (rayon d'environ 4,5 px) dans la couleur
    du contour, puis le texte par-dessus.
  - Ombre : une copie noire translucide décalée.
- **Rectangle penché ou parallélogramme** (barre de pas) : pas de cisaillement possible. Le
  dessiner avec des traits horizontaux qui se chevauchent, dans une couleur opaque, et
  appliquer la transparence au `PartDraw` entier. Avec des traits translucides, les
  chevauchements font des rayures.

### Attributs et structure

- **Valeurs entières obligatoires** : x, y, width et height des `PartText`, `PartImage`,
  `PartDraw`, `Group` et `ComplicationSlot`.
- **Un `ListOption` n'a qu'un enfant** : l'envelopper dans un `Group`.
- **Coordonnées des enfants d'un `Group`** : relatives au Group.
- **Enfants d'un `Compare` ou d'un `Default`** : `Group`, `Condition` ou horloges seulement.
  Envelopper les `PartText`.
- **Couleurs configurables** :
  - un `ColorOption` porte au plus **5 couleurs** ;
  - on ne peut pas mélanger des références de configuration dans une liste de dégradé ;
  - les couleurs dérivées se font par transparence (`alpha` sur PartText ou PartDraw) ;
  - les encres se choisissent par bande, et le générateur vérifie le contraste (au moins 3,5).
- **Gabarits de texte** : pas de « %% » fiable. Mettre le « % » dans un `PartText` séparé ;
  `%s°` fonctionne.
- **Masques** : `renderMode="MASK"` sur un enfant d'un Group découpe les enfants SOURCE du
  même Group, quel que soit leur ordre. Fiable pour les découpes.
- **Effet loupe** : un `Group` avec `scaleX` et `scaleY` (pivot normalisé dans sa boîte),
  plus un `ComplicationSlot` avec `scaleX` et `scaleY`. Fond uni sous la loupe : des bandes
  agrandies laissent un croissant au bord du dôme.

### ComplicationSlot

- **Branche EMPTY** :
  - **[montre]** elle n'est pas dessinée quand l'emplacement n'a pas de source ;
  - la donnée par défaut se dessine donc hors de l'emplacement ;
  - chaque branche non vide redessine d'abord le fond (patch découpé à la forme de
    l'emplacement), puis la donnée de la source.
- **Bounding** : `BoundingBox` ou `BoundingOval` obligatoire. `DefaultProviderPolicy` est
  facultatif, mais s'il est présent il exige un type.
- **Types acceptés** : accepter tous les types du format. Le sélecteur ne propose une source
  que si l'un de ses types est accepté.
  - Liste : `SHORT_TEXT`, `LONG_TEXT`, `RANGED_VALUE`, `GOAL_PROGRESS`,
    `MONOCHROMATIC_IMAGE`, `SMALL_IMAGE`, `PHOTO_IMAGE`, `WEIGHTED_ELEMENTS`, `EMPTY`.
  - Texte d'une source : `[COMPLICATION.TEXT]` et `[COMPLICATION.TITLE]`.
  - Progression : `([COMPLICATION.RANGED_VALUE_VALUE]-MIN)/(MAX-MIN)` ou
    `GOAL_PROGRESS_VALUE/TARGET_VALUE`.
  - Icône : `[COMPLICATION.MONOCHROMATIC_IMAGE]` avec `tintColor`.

### Toucher : `Launch`

- **Valeurs de `target`** : un raccourci système (CALENDAR, BATTERY_STATUS,
  HEALTH_HEART_RATE, ALARM, SETTINGS…) ou un **nom de paquet** (`com.samsung.android.watch.weather`,
  `com.samsung.android.wear.shealth`).
- **Placement** : sur un `Group` dont la boîte est la zone sensible, jamais sur un Group
  plein écran. **[montre]** Fonctionne aussi sous un emplacement vide.

### Données intégrées utiles

- Heure : `[HOUR_0_23_Z]`, `[HOUR_1_12_Z]` (avec `[IS_24_HOUR_MODE]`), `[MINUTE_Z]`,
  `[SECOND]`.
- Date : `[DAY_Z]`, `[MONTH_S]`, `[DAY_OF_WEEK_F]`.
- Santé et batterie : `[HEART_RATE]`, `[BATTERY_PERCENT]`, `[STEP_COUNT]`, `[STEP_PERCENT]`.
- Météo (WFF v2) : `[WEATHER.*]`, avec les codes de condition 1 et 8 (soleil), 14 (nuageux),
  4, 6 et 12 (pluie), 5, 7, 10 et 11 (neige), 9 (orage), 3 et 13 (brouillard).
- **Il n'existe ni calories, ni distance, ni score** parmi les données intégrées du format.
- **Pas de double toucher ni d'appui long** dans aucune version du format (v1 à v5) : seul le
  toucher simple existe (`Launch`, `Images change="TAP"`). Ne pas mettre d'action sur une grande
  zone souvent effleurée (l'heure) : l'utilisateur la déclencherait par accident.
- **Réglage à choix** : `ListConfiguration` déclarée dans `UserConfigurations` (avec
  `ListOption displayName`), puis `<ListConfiguration id>` dans la scène, un `Group` par option.
- **Couleur conditionnelle** (batterie rouge à 20 % ou moins) : `Condition` sur
  `[BATTERY_PERCENT] <= 20`, chaque branche dans un `Group`.

## 3. Samsung Health : ce qu'on peut lire, et où (vérifié)

- **Score d'énergie et score de sommeil** :
  - Samsung a une complication, **réservée à ses propres cadrans** ;
  - elle est absente du sélecteur des cadrans tiers, même avec tous les types acceptés.
- **Samsung Health Data SDK** :
  - **téléphone uniquement** ;
  - **[montre]** sur la montre : erreur 3000 « Samsung Health is not installed » ;
  - utilisable en lecture avec le mode développeur de Samsung Health (téléphone : *À propos*,
    10 touches sur la version, « Developer mode (Samsung Health Data SDK) ») ;
  - **distribution** : accord partenaire Samsung ; le téléchargement officiel demande un compte
    business.
- **API du SDK** (1.0.0, vérifiée par `javap` sur le .aar ; la 1.1.0 ajoute `SleepApnea` et
  `IrregularHeartRhythmNotification`) :
  - instances : `DataTypes.X` ; champs et opérations : `DataType.XType.CHAMP`
    (ex. `EnergyScoreType.ENERGY_SCORE` : Float) ;
  - lecture : `store.readData(DataTypes.X.readDataRequestBuilder…build()).dataList`. Selon le
    type, le builder est un `DualTimeBuilder` (`setLocalTimeFilter`) ou un `LocalDateBuilder`
    (`setLocalDateFilter`, par exemple pour EnergyScore) ;
  - agrégats : `store.aggregateData(DataType.StepsType.TOTAL.requestBuilder…build()).dataList.first().value` ;
    les objectifs passent par `…GoalType.LAST` (`AllSourceLocalDateBuilder`) ;
  - le helper générique doit être `suspend fun <T : Any>` ;
  - la liste complète est dans `energyscore-phone/…/HealthReader.kt`.
- **Health Services (Wear OS, sur la montre)** :
  - mode passif : `STEPS_DAILY`, `DISTANCE_DAILY`, `CALORIES_DAILY`, `FLOORS_DAILY` ;
  - autorisation `ACTIVITY_RECOGNITION` ;
  - service avec la permission `…healthservices.permission.PASSIVE_DATA_BINDING` ;
  - utiliser `health-services-client:1.1.0-alpha05` avec Kotlin 1.9, et la dépendance
    **guava complète** : le paquet `listenablefuture` est résolu en version vide.
- **Health Sensor SDK (montre)** : capteurs bruts (fréquence cardiaque, SpO2, ECG, température
  cutanée), mesures à la demande. Aucun score.

## 4. Architecture d'une appli de complications compagnon (Santé Sync)

- **Téléphone et montre**, avec le **même applicationId et la même clé**, sinon le Data Layer
  ne livre rien.
- **Téléphone** :
  - lit les données, puis `PutDataMapRequest("/sante")` avec `setUrgent` et un horodatage
    pour forcer la livraison ;
  - WorkManager toutes les 30 min ;
  - batterie « non restreinte » conseillée.
- **Montre** :
  - `WearableListenerService` (filtre `DATA_CHANGED` sur `pathPrefix`), puis cache
    SharedPreferences ;
  - puis `ComplicationDataSourceUpdateRequester.requestUpdateAll()`.
- **Un service par complication** : sous-classes générées d'une table unique
  (`energyscore-watch/tools/gen_metrics.py`, qui génère aussi le manifeste et les icônes).
  - Types fournis : `SHORT_TEXT` et `LONG_TEXT`, plus `RANGED_VALUE` (si max ou objectif) et
    `GOAL_PROGRESS` (si objectif).
  - `setTapAction` ouvre Samsung Health. Déclarer le paquet dans `<queries>` (Android 11+).
- **Pièges de l'appli montre** :
  - sans activité LAUNCHER, l'appli semble ne pas s'installer (pas d'icône) ;
  - prévoir une icône adaptative.
- **Tuile et écran Compose (compilés et validés sur la montre)** avec Kotlin 1.9.24 :
  - Compose : `kotlinCompilerExtensionVersion 1.5.14`, `activity-compose:1.9.3`,
    `wear.compose:compose-material` et `compose-foundation` `1.3.1` ; lunette à la main avec
    `onRotaryScrollEvent` + `scrollBy` + `focusRequester` ; `ComponentActivity` attend
    `onRequestPermissionsResult(…, permissions: Array<String>, …)` (pas `Array<out String>`).
  - Tuile : `wear.tiles:tiles:1.4.1` + `wear.protolayout:protolayout:1.2.1`, `TileService` avec
    `Futures.immediateFuture` (Guava), `Arc`/`ArcLine` dans une `Box` pour un anneau,
    `LaunchAction` vers sa propre activité (une tuile ne peut pas ouvrir Samsung Health, il faut
    le nom de classe exact). Rafraîchir avec `TileService.getUpdater(ctx).requestUpdate(…)` à
    chaque donnée reçue. Manifeste : permission `BIND_TILE_PROVIDER`, métadonnée
    `androidx.wear.tiles.PREVIEW` (image). Pas de police personnalisée dans une tuile.

## 5. Publication

- **Cadran WFF** : sans code (`hasCode=false`), donc **fiche séparée** des applis qui ont du
  code.
- **Appli compagnon** : une seule fiche pour le téléphone et la montre (même applicationId).
- **Avant publication** :
  - clé de production et AAB ;
  - santé : confidentialité, « Sécurité des données », déclaration santé ;
  - ne jamais publier une reproduction (Race).

## 6. Pièges du conteneur

- Réseau : Google Maven et dl.google.com sont bloqués. Le validateur WFF compilé est dans le
  scratchpad (`validate.sh <version> <xml>`).
- Playwright : lien temporaire `node_modules -> /opt/node-tools/node_modules`, à supprimer
  avant de committer.
- Reddit n'est pas lisible par Firecrawl. Les pages Samsung chargent leurs exemples de code
  en JavaScript (blocs vides) : lire le .aar avec `javap` ou des dépôts publics.

## 7. Idées

- Méridien (cadran de luxe, textures carbone, bambou, soleillé…) et Strate.
- Appli téléphone compagnon pour installer le cadran.
