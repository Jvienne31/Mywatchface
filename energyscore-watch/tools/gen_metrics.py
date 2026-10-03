#!/usr/bin/env python3
"""Table unique des données Samsung Health transmises téléphone -> montre.

    python3 energyscore-watch/tools/gen_metrics.py

Génère (ne pas éditer à la main) :
  energyscore-watch : Metric.kt, Providers.kt, AndroidManifest.xml, values/metrics.xml,
                      drawable/ic_m_*.xml (une complication par donnée)
  energyscore-phone : Keys.kt (clés du Data Layer, contrat commun aux deux applis)

Chaque ligne : identifiant, libellé du sélecteur, titre court (affiché sous la valeur),
format, clé d'objectif (ou None), maximum fixe (ou None), valeur et objectif d'aperçu,
pictogramme.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WATCH = os.path.join(ROOT, "energyscore-watch", "src", "main")
PHONE = os.path.join(ROOT, "energyscore-phone", "src", "main")
WPKG = "com/jvienne/energyscore/watch"
PPKG = "com/jvienne/energyscore/phone"

# id, libellé, titre, format, objectif, max, aperçu, aperçu objectif, icône
METRICS = [
    ("energy", "Score d'énergie", "ÉNERGIE", "INT", None, 100, 82, None, "bolt"),
    ("sleep_score", "Score de sommeil", "SOMMEIL", "INT", None, 100, 78, None, "moon_star"),
    ("sleep_min", "Durée de sommeil", "SOMMEIL", "DURATION", "sleep_goal_min", None, 389, 450, "moon"),
    ("steps", "Pas (objectif)", "PAS", "INT", "steps_goal", None, 6420, 10000, "steps"),
    ("distance_m", "Distance du jour", "DISTANCE", "DISTANCE", None, None, 4230, None, "pin"),
    ("active_kcal", "Calories actives", "KCAL ACT.", "INT", "active_kcal_goal", None, 412, 500, "flame"),
    ("total_kcal", "Calories totales", "KCAL", "INT", None, None, 2140, None, "flame"),
    ("active_min", "Temps actif", "ACTIF", "DURATION", "active_min_goal", None, 48, 90, "timer"),
    ("floors", "Étages", "ÉTAGES", "INT", None, None, 8, None, "stairs"),
    ("water_ml", "Eau bue", "EAU", "WATER", "water_goal_ml", None, 1250, 2000, "drop"),
    ("food_kcal", "Calories consommées", "REPAS", "INT", "food_kcal_goal", None, 1450, 2200, "food"),
    ("hr_last", "Fréquence cardiaque (dernière)", "BPM", "INT", None, 200, 68, None, "heart"),
    ("hr_min", "Fréquence cardiaque min du jour", "FC MIN", "INT", None, 200, 52, None, "heart"),
    ("hr_max", "Fréquence cardiaque max du jour", "FC MAX", "INT", None, 200, 141, None, "heart"),
    ("spo2", "Oxygène dans le sang", "SpO2", "PERCENT", None, 100, 96, None, "drop_o"),
    ("skin_temp", "Température cutanée", "PEAU", "TEMP", None, None, 33.4, None, "thermo"),
    ("body_temp", "Température corporelle", "TEMP.", "TEMP", None, None, 36.8, None, "thermo"),
    ("bp_sys", "Tension artérielle", "TENSION", "PRESSURE", None, None, 121, None, "heart_pulse"),
    ("glucose", "Glycémie", "GLYCÉMIE", "DEC1", None, None, 5.4, None, "drop"),
    ("weight", "Poids", "POIDS", "KG", None, None, 78.4, None, "scale"),
    ("body_fat", "Masse grasse", "M. GRASSE", "PERCENT", None, 100, 21.5, None, "person"),
    ("muscle", "Masse musculaire squelettique", "MUSCLE", "KG", None, None, 34.2, None, "person"),
    ("bmi", "IMC", "IMC", "DEC1", None, None, 24.1, None, "person"),
    ("vo2max", "VO2 max (dernière séance)", "VO2 MAX", "DEC1", None, None, 44.7, None, "runner"),
    ("last_ex_min", "Dernière séance : durée", "SÉANCE", "DURATION", None, None, 42, None, "runner"),
    ("last_ex_m", "Dernière séance : distance", "SÉANCE", "DISTANCE", None, None, 8120, None, "runner"),
]
# Valeurs transmises sans complication propre (objectifs, 2e valeur de la tension)
EXTRA_KEYS = ["sleep_goal_min", "steps_goal", "active_kcal_goal", "active_min_goal", "water_goal_ml",
              "food_kcal_goal", "bp_dia"]


def ellipse(cx, cy, rx, ry):
    return f"M{cx - rx},{cy}a{rx},{ry} 0 1,0 {2 * rx},0a{rx},{ry} 0 1,0 {-2 * rx},0Z"


# Pictogrammes 24 x 24 (blancs : la montre les recolore)
ICONS = {
    "bolt": "M13,2L4.1,12.1C3.65,12.6 4,13.4 4.65,13.4H11L10,22L19.8,10.5C20.3,9.9 19.9,9.1 19.2,9.1H13Z",
    "moon": "M12.3,2A9.5,9.5 0,1 0,22,13.7A7.5,7.5 0,0 1,12.3,2Z",
    "moon_star": "M11.3,3A9,9 0,1 0,21,13.7A7,7 0,0 1,11.3,3Z"
                  "M18,2L18.9,4.1L21,5L18.9,5.9L18,8L17.1,5.9L15,5L17.1,4.1Z",
    "steps": ellipse(8, 8.5, 3, 4.6) + ellipse(8, 16, 2.2, 1.9) + ellipse(16, 5.5, 3, 4.6) + ellipse(16, 13, 2.2, 1.9),
    "pin": "M12,2a7,7 0,0 0,-7,7c0,5.2 7,13 7,13s7,-7.8 7,-13a7,7 0,0 0,-7,-7Zm0,4.5a2.5,2.5 0,1 1,0,5a2.5,2.5 0,1 1,0,-5Z",
    "flame": "M12,2c4.5,4.5 7,8 7,12a7,7 0,0 1,-14,0c0,-3 1.6,-5 3.4,-6.6c0.2,2.4 1.2,3.6 2.6,3.6"
             "c1.4,0 2,-1.4 1.6,-3.4C12.2,5.8 11.6,4 12,2Z",
    "timer": "M10,1h4v2h-4Z" + ellipse(12, 13.5, 8.5, 8.5) + "M12,7.5a6,6 0,1 0,0.01,0ZM11,9h2v5.2l-2.6,2.2l-1.3,-1.5l1.9,-1.6Z",
    "stairs": "M3,21v-4h4v-4h4v-4h4V5h6v4h-2v-2h-2v4h-4v4h-4v4h-4v2Z",
    "drop": "M12,2.5C16.5,8 18.5,11.5 18.5,14.5a6.5,6.5 0,0 1,-13,0C5.5,11.5 7.5,8 12,2.5Z",
    "drop_o": "M12,2.5C16.5,8 18.5,11.5 18.5,14.5a6.5,6.5 0,0 1,-13,0C5.5,11.5 7.5,8 12,2.5Z"
              "M12,11.5a3,3 0,1 0,0.01,0Z",
    "food": "M6,2v7a2,2 0,0 0,1.5,1.9V22h2V10.9A2,2 0,0 0,11,9V2h-1.3v6h-0.9V2h-1.2v6h-0.9V2Z"
            "M17,2c-1.9,0 -3.3,2.2 -3.3,5.5V14h2.3v8h2V2Z",
    "heart": "M12,21C5,16 2.5,12.3 2.5,8.6C2.5,5.6 4.8,3.5 7.5,3.5c1.9,0 3.4,1 4.5,2.6c1.1,-1.6 2.6,-2.6 4.5,-2.6"
             "c2.7,0 5,2.1 5,5.1C21.5,12.3 19,16 12,21Z",
    "heart_pulse": "M12,21C5,16 2.5,12.3 2.5,8.6C2.5,5.6 4.8,3.5 7.5,3.5c1.9,0 3.4,1 4.5,2.6c1.1,-1.6 2.6,-2.6 4.5,-2.6"
                   "c2.7,0 5,2.1 5,5.1C21.5,12.3 19,16 12,21Z"
                   "M4,11h4l1.5,-3l2.5,6l2,-4l1,1h5v1.6h-5.6l-0.3,-0.3l-2.2,4.4l-2.5,-6l-0.9,1.9H4Z",
    "thermo": "M12,2a3,3 0,0 0,-3,3v9.3a4.5,4.5 0,1 0,6,0V5a3,3 0,0 0,-3,-3Zm0,2a1,1 0,0 1,1,1v10.3l0.4,0.3"
              "a2.5,2.5 0,1 1,-2.8,0l0.4,-0.3V5a1,1 0,0 1,1,-1Z",
    "scale": "M5,3h14a2,2 0,0 1,2,2v14a2,2 0,0 1,-2,2H5a2,2 0,0 1,-2,-2V5a2,2 0,0 1,2,-2Z"
             "M12,6a5,5 0,0 0,-4.8,3.6l2,0.8a3,3 0,0 1,5.6,0l2,-0.8A5,5 0,0 0,12,6Z",
    "person": ellipse(12, 4.5, 2.5, 2.5) + "M8.5,8.5h7l1.2,7h-2.2l-0.6,6.5h-3.8l-0.6,-6.5H7.3Z",
    "runner": ellipse(14.5, 4, 2.2, 2.2) + "M11,7.5l4,0.6l2.3,3.4l2.7,0.5l-0.4,2l-3.6,-0.8l-1.2,-1.6l-1.1,3.6l2.6,2.2"
              "l-0.6,5.6h-2.1l0.4,-4.4l-2.9,-2.3l-1.3,2.6l-4.4,1.2l-0.5,-2l3.4,-0.9l2.2,-6.4l-1.6,-0.2l-1.6,2.6"
              "l-1.8,-1.1Z",
}


def camel(s):
    return "".join(p.capitalize() for p in s.split("_"))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def types_for(m):
    _, _, _, _, goal, mx, *_ = m
    t = ["SHORT_TEXT", "LONG_TEXT"]
    if goal or mx:
        t.append("RANGED_VALUE")
    if goal:
        t.append("GOAL_PROGRESS")
    return ",".join(t)


def fl(v):
    return "null" if v is None else f"{float(v)}f"


def gen():
    head = "// FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py : ne pas éditer à la main.\n"
    keys = [m[0] for m in METRICS] + EXTRA_KEYS

    # --- téléphone : clés ---
    lines = [head, "package com.jvienne.energyscore.phone", "",
             "/** Clés des valeurs envoyées à la montre (chemin Data Layer [PATH]). */",
             "object Keys {", '    const val PATH = "/sante"', '    const val TIMESTAMP = "ts"']
    lines += [f'    const val {k.upper()} = "{k}"' for k in keys]
    lines += ["", "    /** Libellés affichés dans l'appli téléphone (même ordre que sur la montre). */",
              "    val LABELS = linkedMapOf("]
    lines += [f'        {m[0].upper()} to "{m[1]}",' for m in METRICS]
    lines += ["    )", "}", ""]
    write(os.path.join(PHONE, "java", PPKG, "Keys.kt"), "\n".join(lines))

    # --- montre : Metric.kt ---
    lines = [head, "package com.jvienne.energyscore.watch", "",
             "/** Données affichables en complication (une par fournisseur, cf. Providers.kt). */",
             "enum class Metric(",
             "    val key: String,",
             "    val label: String,",
             "    val title: String,",
             "    val format: Format,",
             "    val goalKey: String?,",
             "    val max: Float?,",
             "    val preview: Float,",
             "    val previewGoal: Float?,",
             "    val icon: Int,",
             ") {"]
    for m in METRICS:
        mid, label, title, fmt, goal, mx, prev, pgoal, icon = m
        g = f'"{goal}"' if goal else "null"
        lab = label.replace('"', '\\"')
        lines.append(f'    {mid.upper()}("{mid}", "{lab}", "{title}", Format.{fmt}, {g}, {fl(mx)}, '
                     f'{fl(prev)}, {fl(pgoal)}, R.drawable.ic_m_{icon}),')
    lines[-1] = lines[-1].rstrip(",") + ";"
    lines += ["}", ""]
    write(os.path.join(WATCH, "java", WPKG, "Metric.kt"), "\n".join(lines))

    # --- montre : un service par donnée ---
    lines = [head, "package com.jvienne.energyscore.watch", ""]
    for m in METRICS:
        lines.append(f"class {camel(m[0])}Provider : MetricComplicationService() "
                     f"{{ override val metric = Metric.{m[0].upper()} }}")
    lines += ["", "/** Tous les fournisseurs, pour demander leur mise à jour à la réception de données. */",
              "val ALL_PROVIDERS = listOf("]
    lines += [f"    {camel(m[0])}Provider::class.java," for m in METRICS]
    lines += [")", ""]
    write(os.path.join(WATCH, "java", WPKG, "Providers.kt"), "\n".join(lines))

    # --- montre : libellés ---
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             "<!-- FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py -->", "<resources>"]
    for m in METRICS:
        lines.append(f'    <string name="m_{m[0]}">{m[1].replace(chr(39), chr(92) + chr(39))}</string>')
    lines += ["</resources>", ""]
    write(os.path.join(WATCH, "res", "values", "metrics.xml"), "\n".join(lines))

    # --- montre : pictogrammes ---
    for name, d in ICONS.items():
        write(os.path.join(WATCH, "res", "drawable", f"ic_m_{name}.xml"),
              '<?xml version="1.0" encoding="utf-8"?>\n'
              '<!-- FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py -->\n'
              '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
              '    android:width="24dp" android:height="24dp"\n'
              '    android:viewportWidth="24" android:viewportHeight="24">\n'
              f'    <path android:fillColor="#FFFFFFFF" android:fillType="evenOdd"\n'
              f'        android:pathData="{d}" />\n'
              '</vector>\n')

    # --- montre : manifeste ---
    svc = []
    for m in METRICS:
        svc.append(f'''        <service
            android:name=".{camel(m[0])}Provider"
            android:exported="true"
            android:icon="@drawable/ic_m_{m[8]}"
            android:label="@string/m_{m[0]}"
            android:permission="com.google.android.wearable.permission.BIND_COMPLICATION_PROVIDER">
            <intent-filter>
                <action android:name="android.support.wearable.complications.ACTION_COMPLICATION_UPDATE_REQUEST" />
            </intent-filter>
            <meta-data
                android:name="android.support.wearable.complications.SUPPORTED_TYPES"
                android:value="{types_for(m)}" />
            <meta-data
                android:name="android.support.wearable.complications.UPDATE_PERIOD_SECONDS"
                android:value="0" />
        </service>
''')
    write(os.path.join(WATCH, "AndroidManifest.xml"), f'''<?xml version="1.0" encoding="utf-8"?>
<!-- FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py : ne pas éditer à la main. -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-feature android:name="android.hardware.type.watch" />

    <!-- Pas, distance, calories, étages en direct (Health Services) -->
    <uses-permission android:name="android.permission.ACTIVITY_RECOGNITION" />

    <!-- Toucher une complication ouvre Samsung Health sur la montre -->
    <queries>
        <package android:name="com.samsung.android.wear.shealth" />
    </queries>

    <application
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:allowBackup="false">

        <!-- Écran de l'appli (icône dans la liste des applis) : toutes les données, en Compose. -->
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:theme="@android:style/Theme.DeviceDefault">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <!-- L'appli téléphone fait la lecture Samsung Health : la montre n'en dépend pas pour
             s'installer, mais ses données viennent du téléphone. -->
        <meta-data
            android:name="com.google.android.wearable.standalone"
            android:value="true" />

        <!-- Reçoit les valeurs du jour mesurées par la montre (Health Services, mode passif) -->
        <service
            android:name=".PassiveDataService"
            android:exported="true"
            android:permission="com.google.android.wearable.healthservices.permission.PASSIVE_DATA_BINDING" />

        <!-- Reçoit les données poussées par l'appli téléphone (Data Layer, chemin /sante). -->
        <service
            android:name=".HealthSyncListenerService"
            android:exported="true">
            <intent-filter>
                <action android:name="com.google.android.gms.wearable.DATA_CHANGED" />
                <data
                    android:scheme="wear"
                    android:host="*"
                    android:pathPrefix="/sante" />
            </intent-filter>
        </service>

        <!-- Tuile « Santé du jour » : on glisse vers la gauche depuis le cadran -->
        <service
            android:name=".SanteTileService"
            android:exported="true"
            android:label="@string/tile_label"
            android:icon="@drawable/ic_m_bolt"
            android:permission="com.google.android.wearable.permission.BIND_TILE_PROVIDER">
            <intent-filter>
                <action android:name="androidx.wear.tiles.action.BIND_TILE_PROVIDER" />
            </intent-filter>
            <meta-data
                android:name="androidx.wear.tiles.PREVIEW"
                android:resource="@drawable/tile_preview" />
        </service>

        <!-- Une complication par donnée Samsung Health -->
{"".join(svc)}
    </application>
</manifest>
''')
    print(f"{len(METRICS)} données, {len(ICONS)} pictogrammes")


if __name__ == "__main__":
    gen()
