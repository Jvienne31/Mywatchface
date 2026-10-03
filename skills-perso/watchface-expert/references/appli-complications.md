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
