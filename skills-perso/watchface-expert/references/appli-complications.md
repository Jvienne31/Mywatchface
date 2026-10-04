# Appli de complications compagnon (téléphone et montre)

Modèle éprouvé : Santé Sync. Le téléphone lit Samsung Health, la montre sert 26
complications.

## Architecture

```
Téléphone (Samsung Health Data SDK)            Montre (complications)
 HealthReader.readAll() → Map<clé, Float>        WearableListenerService (DATA_CHANGED, /sante)
 WatchSync : PutDataMapRequest("/sante")  ──►    cache SharedPreferences (remplacé à chaque envoi)
   .setUrgent() + horodatage (force l'envoi)     + PassiveListenerService (Health Services, en direct)
 WorkManager toutes les 30 min + bouton          → ComplicationDataSourceUpdateRequester.requestUpdateAll()
                                                 → un SuspendingComplicationDataSourceService par donnée
```

- **Même identifiant d'application et même clé de signature** sur les deux APK. Sinon le Data
  Layer ne livre **rien**, sans aucune erreur.
- **Modèle hybride** (recommandé par Google) : la montre affiche ses mesures en direct sans le
  téléphone, et le téléphone enrichit ces données.

## Montre

- **Une complication par service.** Une classe de base abstraite (`MetricComplicationService`)
  et des sous-classes d'une ligne, **générées** depuis une table Python unique. La table
  génère aussi le manifeste, les libellés, les icônes vectorielles et les clés partagées avec
  le téléphone.
- **Types fournis** :
  - `SHORT_TEXT` et `LONG_TEXT` toujours, avec `setTitle` (titre court en majuscules) et
    `setMonochromaticImage` ;
  - `RANGED_VALUE` si la donnée a un objectif ou un maximum ;
  - `GOAL_PROGRESS` si elle a un objectif (API 33 et plus).
- **Textes courts**, pour tenir dans un dôme : `6h29`, `4,2 km`, `1,2 L`, `78,4 kg`,
  `120/80`, avec la locale FR.
- **Toucher** : `setTapAction(PendingIntent)` vers l'appli qui contient le détail (Samsung
  Health montre : `com.samsung.android.wear.shealth`). Déclarer le paquet dans `<queries>`
  (visibilité Android 11 et plus).
- **Manifeste de chaque service** : permission `BIND_COMPLICATION_PROVIDER`, action
  `ACTION_COMPLICATION_UPDATE_REQUEST`, métadonnées `SUPPORTED_TYPES`, et
  `UPDATE_PERIOD_SECONDS=0` (mises à jour poussées).
- **Écran et icône obligatoires.**
  - Sans activité `LAUNCHER`, l'appli « ne s'installe pas » aux yeux de l'utilisateur, car
    il ne voit aucune icône.
  - Ajouter une activité de contrôle (valeurs reçues, autorisations) et une **icône
    adaptative** (`mipmap-anydpi/ic_launcher.xml` : fond, avant-plan dans la zone sûre de
    66 dp, monochrome). Un vecteur blanc seul s'affiche comme un rond blanc.

## Tuile et écran Compose (compilés et validés sur la montre, Kotlin 1.9.24)

- **Compose for Wear OS** :
  - `kotlinCompilerExtensionVersion 1.5.14`, `activity-compose:1.9.3`, puis
    `wear.compose:compose-material` et `compose-foundation` en 1.3.1 ;
  - lunette tournante à brancher soi-même : `onRotaryScrollEvent`, puis `scrollBy` et
    `focusRequester` ;
  - avec `ComponentActivity`, la signature est
    `onRequestPermissionsResult(…, permissions: Array<String>, …)` : `Array<out String>` ne
    compile pas.
- **Tuile** :
  - dépendances `wear.tiles:tiles:1.4.1` et `wear.protolayout:protolayout:1.2.1` ;
  - `TileService` avec `Futures.immediateFuture` (Guava) ;
  - anneau : un `Arc` et un `ArcLine` dans une `Box` ;
  - toucher : `LaunchAction` vers sa propre activité. Ouvrir une autre appli exige le nom exact
    de sa classe, que Samsung Health ne publie pas ;
  - rafraîchissement : `TileService.getUpdater(ctx).requestUpdate(…)` à chaque donnée reçue ;
  - manifeste : permission `BIND_TILE_PROVIDER` et métadonnée `androidx.wear.tiles.PREVIEW`
    (une image) ;
  - pas de police personnalisée dans une tuile.

## Téléphone

- **Lecture.** Chaque donnée est lue dans son propre `try` : une permission refusée ou une
  donnée absente n'empêche pas les autres.
- **Autorisations.** Demander toutes les permissions de lecture d'un coup. Gérer
  `ResolvablePlatformException.resolve(activity)` (Samsung Health absent ou mode développeur
  désactivé).
- **Synchronisation.** WorkManager périodique (30 min, `KEEP`). Conseiller de mettre la
  batterie de l'appli en « Non restreinte ».

## CI et compilation

- **Bloc commun du `build.gradle`** :
  - `signingConfigs.debug` sur un `debug.keystore` versionné (mots de passe standard
    `android`) ;
  - `applicationId` identique sur les deux modules.
- **SDK propriétaire** :
  - ne pas le versionner (`.gitignore`) ;
  - en CI, le télécharger à un commit figé et vérifier son SHA-256 ;
  - documenter l'alternative officielle.
- **Journaux de CI.** Les journaux de GitHub Actions sont hébergés sur un stockage que le
  conteneur ne peut pas joindre : utiliser l'outil MCP GitHub `get_job_logs`
  (`failed_only=true`).
- **Erreurs déjà rencontrées** :
  - `Type argument is not within its bounds: should be subtype of 'Any'` : borne `<T : Any>`
    sur les helpers génériques du SDK ;
  - `Cannot access class ListenableFuture` : ajouter guava `-android` complet.

## Publication

- **Cadran WFF** : fiche à part, car il est sans code (`hasCode=false`).
- **Appli compagnon** : **une** fiche pour le téléphone et la montre (même applicationId),
  avec un AAB par appareil.
- **Avant publication** :
  - clé de production (jamais la clé debug) ;
  - politique de confidentialité, section « Sécurité des données », déclaration des applis de
    santé ;
  - justification de `ACTIVITY_RECOGNITION` ;
  - accord partenaire Samsung pour le Health Data SDK.
- **Ne jamais publier une reproduction** d'un cadran existant.

## Watch Face Push et Kotlin 2 (en place dans Santé Sync, compilé le 4 octobre 2026)

- **Outillage minimum** :
  - Kotlin 2.1.21 avec le plugin `org.jetbrains.kotlin.plugin.compose` (remplace
    `composeOptions`) ;
  - AGP 8.9.1 et Gradle 8.11.1 ;
  - `compileSdk 36` pour l'appli qui utilise `androidx.wear.watchfacepush:watchfacepush:1.0.0`.
    Le contrôle des métadonnées AAR échoue sinon.
  - `<uses-sdk tools:overrideLibrary="androidx.wear.watchfacepush"/>` et un test
    `SDK_INT >= 36` pour garder `minSdk 33`.
- **Cadran poussé** :
  - paquet `<appli>.watchfacepush.<nom>` : une variante Gradle (`productFlavors push`) ;
  - manifeste sans `<service>`, retiré avec `tools:node="remove"` dans `src/push`. Seuls
    `manifest`, `uses-feature`, `uses-sdk`, `application`, `property` et `meta-data` sont admis ;
  - `minifyEnabled true` (pas de dex) et `hasCode="false"`.
- **Validateur** :
  - `validator-push-cli-1.1.0-alpha01.jar` sur `dl.google.com/android/maven2`. La version
    « alpha10 » citée par la documentation n'existe pas (404) ; c'est un jar autonome ;
  - sortie : « Validation is successful » puis « No failing checks detected, generated token:
    <jeton> », suivi de 10 contrôles (taille, contenu, manifeste, présence du WFF, validateur
    WFF, mémoire, version WFF, minSdk, nom de paquet, signature).
- **Appli** :
  - API : `WatchFacePushManagerFactory.createWatchFacePushManager(ctx)`, puis `listWatchFaces()`
    (`installedWatchFaceDetails` : `slotId`, `packageName`, `versionCode`), `addWatchFace(fd,
    jeton)`, `updateWatchFace(slotId, fd, jeton)`, `setWatchFaceAsActive(slotId)`
    (autorisation `SET_PUSHED_WATCH_FACE_AS_ACTIVE`) et `isWatchFaceActive(paquet)` ;
  - permission `PUSH_WATCH_FACES` ;
  - l'APK est passé par `ParcelFileDescriptor.open(fichier)`.
- **Tuile Material 3** : `protolayout-material3:1.3.0` avec `tiles:1.5.0` compile sous AGP 8.9.
  - Fonctions : `materialScope(ctx, device, allowDynamicTheme=false,
    defaultColorScheme=ColorScheme(...))`, puis `primaryLayout(titleSlot, mainSlot, bottomSlot,
    margins)`, `graphicDataCard`, `textDataCard`, `buttonGroup { buttonGroupItem { } }`,
    `circularProgressIndicator`, `textEdgeButton`, `String.layoutString`, `LayoutColor(argb)` et
    `clickable(launchAction(ComponentName), id)`.
  - Les API 1.4 des exemples Google (`materialScopeWithResources`, `ProtoLayoutScope`) exigent
    AGP 9.
  - La liste exacte des signatures d'une version :
    `raw.githubusercontent.com/androidx/androidx/androidx-main/<chemin>/api/<version>.txt`.
