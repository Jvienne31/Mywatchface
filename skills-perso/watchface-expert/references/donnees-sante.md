# Données santé : ce qu'un cadran peut afficher, et comment

## Arbre de décision

| Donnée voulue | Voie |
|---|---|
| Heure, date, batterie, pas, % objectif pas, fréquence cardiaque, météo | **Tag WFF** directement dans le cadran |
| Calories, distance, étages (du jour) | **Health Services** sur la montre (appli compagnon, mode passif), ou complication Samsung Health si elle est proposée |
| **Score d'énergie, score de sommeil**, durée de sommeil, objectifs, poids, IMC, masse grasse, tension, glycémie, eau, repas, SpO2, température, VO2 max, dernière séance | **Samsung Health Data SDK sur le téléphone**, envoi par le **Data Layer** à une appli montre qui les sert en complications |
| Capteurs bruts à la demande (fréquence cardiaque, SpO2, ECG, température cutanée, activité électrodermale) | **Samsung Health Sensor SDK** (montre) : mesures, pas de scores |

## Faits vérifiés (à ne pas re-débattre)

### Score d'énergie et score de sommeil

- **Complication réservée.** Samsung a une complication « Score d'énergie », apparue dans
  Info Board en 2024. Elle n'est proposée **qu'à ses propres cadrans**.
  - Elle est absente du sélecteur d'un cadran tiers, même quand l'emplacement accepte tous les
    types.
  - Wear OS permet ce filtrage avec `SAFE_WATCH_FACES`.
- **Liste Samsung Health proposée aux cadrans tiers** (One UI 8 Watch) : Activité
  quotidienne, Cardio, Composition corporelle, Consommées, Eau, Oxygène dans le sang,
  Partage, Pas, Respiration, Sommeil, Stress, Suivi du cycle.

### Health Data SDK

- **Téléphone uniquement** : « Target device: Android smartphones » (notes de version
  1.1.0, mars 2026).
  - **[montre]** Testé sur la montre : `ResolvablePlatformException` code **3000**, « Samsung
    Health is not installed ».
- **Lecture sans accord partenaire.** Activer le mode développeur dans Samsung Health sur le
  téléphone :
  1. *Paramètres > À propos* ;
  2. toucher le numéro de version une dizaine de fois ;
  3. activer « Developer mode (Samsung Health Data SDK) ».
  - Les champs « Access code » et « Client ID » ne servent qu'à l'**écriture** : les laisser
    vides.
- **Distribution.** Le mode développeur ne sert qu'aux tests.
  - Diffuser l'appli exige un **accord partenaire** Samsung.
  - Le téléchargement officiel du SDK demande un compte Samsung **business**.
  - Une copie publique du `.aar` 1.0.0 existe dans le dépôt MIT
    `the-momentum/open_wearables_android_sdk`
    (`sdk/libs/maven/com/samsung/android/health/data/1.0.0/data-1.0.0.aar`, SHA-256 `7fd190ea…`).
    Elle convient à une compilation de test, pas à une publication.
- **Versions.** La 1.1.0 ajoute `SleepApneaType` et `IrregularHeartRhythmNotificationType`.
  La 1.0.0 a déjà `EnergyScoreType` et `vo2Max` dans `ExerciseSession`.
- **Mise en œuvre.** Le SDK n'accepte que `minSdk 29`. Il faut aussi le plugin
  `kotlin-parcelize` et gson. Les métadonnées Kotlin sont en 1.8, donc Kotlin 1.9 convient.

## API Health Data SDK : signatures exactes (javap sur le .aar 1.0.0)

**Instances** : `DataTypes.X` (`ENERGY_SCORE`, `SLEEP`, `STEPS`, `HEART_RATE`…).
**Champs et opérations** : `DataType.XType.CHAMP`, accessibles comme membres statiques.

```kotlin
val store = HealthDataService.getStore(context)
// Permissions (l'écran d'autorisation demande une Activity)
val perms = types.map { Permission.of(it, AccessType.READ) }.toSet()
store.getGrantedPermissions(perms)            // suspend
store.requestPermissions(perms, activity)     // suspend, renvoie les permissions accordées

// Lecture : le builder dépend du type
store.readData(DataTypes.ENERGY_SCORE.readDataRequestBuilder        // LocalDateBuilder
    .setLocalDateFilter(LocalDateFilter.of(today.minusDays(1), today.plusDays(1)))
    .setOrdering(Ordering.DESC).setLimit(1).build()).dataList
    .firstOrNull()?.getValue(DataType.EnergyScoreType.ENERGY_SCORE)  // Float

store.readData(DataTypes.SLEEP.readDataRequestBuilder               // DualTimeBuilder
    .setLocalTimeFilter(LocalTimeFilter.of(now.minusDays(2), now))
    .setOrdering(Ordering.DESC).setLimit(1).build())
// champs : SleepType.SLEEP_SCORE (Int), DURATION (Duration), SESSIONS

// Agrégats : le helper générique DOIT être <T : Any>
suspend fun <T : Any> agg(r: AggregateRequest<T>): T? = store.aggregateData(r).dataList.firstOrNull()?.value
agg(DataType.StepsType.TOTAL.requestBuilder.setLocalTimeFilter(sinceMidnight).build())   // Long
agg(DataType.StepsGoalType.LAST.requestBuilder.setLocalDateFilter(todayOnly).build())    // Int
```

| Type | Lecture (builder) | Champs ou agrégats |
|---|---|---|
| EnergyScore | LocalDate | `ENERGY_SCORE` (Float) |
| Sleep | DualTime | `SLEEP_SCORE` Int, `DURATION` Duration, `SESSIONS` ; agrégat `TOTAL_DURATION` (LocalDate) |
| SleepGoal | — | `LAST_BED_TIME`, `LAST_WAKE_UP_TIME` (LocalTime, AllSourceLocalDate) |
| Steps / StepsGoal | — | `TOTAL` Long (LocalTime) / `LAST` Int (AllSourceLocalDate) |
| ActivitySummary | — | `TOTAL_DISTANCE` m, `TOTAL_ACTIVE_CALORIES_BURNED`, `TOTAL_CALORIES_BURNED` (Float), `TOTAL_ACTIVE_TIME` Duration (LocalTime) |
| ActiveCaloriesBurnedGoal / ActiveTimeGoal | — | `LAST` Int / Duration |
| FloorsClimbed | DualTime | `TOTAL` Float (LocalTime), `FLOOR` |
| WaterIntake / Goal | DualTime | `TOTAL` Float (DualTime), `AMOUNT` / `LAST` |
| Nutrition / NutritionGoal | DualTime | `TOTAL_CALORIES` (DualTime) / `LAST_CALORIES` |
| HeartRate | DualTime | `HEART_RATE`, `MIN_HEART_RATE`, `MAX_HEART_RATE` ; agrégats `MIN` / `MAX` (LocalDate) |
| BloodOxygen | DualTime | `OXYGEN_SATURATION` (%) |
| SkinTemperature / BodyTemperature | DualTime | `SKIN_TEMPERATURE` / `BODY_TEMPERATURE` |
| BloodPressure | DualTime | `SYSTOLIC`, `DIASTOLIC`, `MEAN`, `PULSE_RATE` |
| BloodGlucose | DualTime | `GLUCOSE_LEVEL` |
| BodyComposition | DualTime | `WEIGHT`, `BODY_FAT`, `SKELETAL_MUSCLE_MASS`, `BODY_MASS_INDEX`, `BASAL_METABOLIC_RATE`… |
| Exercise | DualTime | `SESSIONS`, puis `ExerciseSession.duration`, `distance`, `calories`, `vo2Max`, `meanHeartRate`… |
| UserProfile | UserProfileBuilder | `HEIGHT`, `WEIGHT`, `GENDER`, `DATE_OF_BIRTH` |

- **Erreurs** : `ResolvablePlatformException` (`hasResolution`, `resolve(activity)`), qui
  hérite de `HealthDataException` (`errorCode`, `errorMessage`).
- **Exemples de code Samsung** : ils sont chargés en JavaScript, donc vides quand on les lit
  par extraction automatique. Lire plutôt le `.aar` avec `javap`, ou du code public existant.

## Health Services (montre, en direct)

- **Dépendances** :
  - `androidx.health:health-services-client:1.1.0-alpha05` pour Kotlin 1.9 (la 1.1.0 stable de
    septembre 2026 vise des outils plus récents) ;
  - `com.google.guava:guava:<x>-android` : le paquet `listenablefuture:1.0` est résolu en
    version vide (9999.0-empty), d'où l'erreur « Cannot access ListenableFuture ».
- **Mode passif** :
  - `PassiveListenerConfig.builder().setDataTypes(setOf(DataType.STEPS_DAILY,
    DISTANCE_DAILY, CALORIES_DAILY, FLOORS_DAILY))` ;
  - puis `HealthServices.getClient(ctx).passiveMonitoringClient.setPassiveListenerServiceAsync(Service::class.java, config)`.
- **Service** :
  - classe `PassiveListenerService`, méthode `onNewDataPointsReceived(DataPointContainer)` ;
  - lecture : `getData(DataType.STEPS_DAILY).lastOrNull()?.value` ;
  - déclaration dans le manifeste avec la permission
    `com.google.android.wearable.healthservices.permission.PASSIVE_DATA_BINDING`.
- **Autorisation** : `ACTIVITY_RECOGNITION`, demandée à l'exécution depuis une Activity.
  Réinscrire l'écoute régulièrement, par exemple à chaque réception de données.
- **Écart avec Samsung Health** : Health Services ne compte que la montre, alors que Samsung
  Health fusionne téléphone et montre. Les chiffres diffèrent légèrement.

## Applis tierces existantes (pour comparer)

| Appli | Données | Modèle |
|---|---|---|
| Wear OS Toolset (GS Watchfaces) | pas, cœur, calories, distance, étages | abonnement ; « peut partager la position » |
| Health Plugin for Wear OS (amoledwatchfaces) | idem | 1,79 $ ; aucune donnée collectée |
| Complications Suite | outils divers, eau saisie à la main | gratuite |

Aucune n'affiche le score d'énergie ni le score de sommeil.
