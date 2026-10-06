// FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py : ne pas éditer à la main.

package com.jvienne.energyscore.watch

/** Données affichables en complication (une par fournisseur, cf. Providers.kt). */
enum class Metric(
    val key: String,
    val label: String,
    val title: String,
    val format: Format,
    val goalKey: String?,
    val max: Float?,
    val preview: Float,
    val previewGoal: Float?,
    val icon: Int,
) {
    ENERGY("energy", "Score d'énergie", "ÉNERGIE", Format.INT, null, 100.0f, 82.0f, null, R.drawable.ic_m_bolt),
    SLEEP_SCORE("sleep_score", "Score de sommeil", "SOMMEIL", Format.INT, null, 100.0f, 78.0f, null, R.drawable.ic_m_moon_star),
    SLEEP_MIN("sleep_min", "Durée de sommeil", "SOMMEIL", Format.DURATION, "sleep_goal_min", null, 389.0f, 450.0f, R.drawable.ic_m_moon),
    STEPS("steps", "Pas (objectif)", "PAS", Format.INT, "steps_goal", null, 6420.0f, 10000.0f, R.drawable.ic_m_steps),
    DISTANCE_M("distance_m", "Distance du jour", "DISTANCE", Format.DISTANCE, "distance_goal_m", null, 4230.0f, 6600.0f, R.drawable.ic_m_pin),
    ACTIVE_KCAL("active_kcal", "Calories actives", "KCAL ACT.", Format.INT, "active_kcal_goal", null, 412.0f, 500.0f, R.drawable.ic_m_flame),
    TOTAL_KCAL("total_kcal", "Calories totales", "KCAL", Format.INT, null, null, 2140.0f, null, R.drawable.ic_m_flame),
    ACTIVE_MIN("active_min", "Temps actif", "ACTIF", Format.DURATION, "active_min_goal", null, 48.0f, 90.0f, R.drawable.ic_m_timer),
    FLOORS("floors", "Étages", "ÉTAGES", Format.INT, null, null, 8.0f, null, R.drawable.ic_m_stairs),
    WATER_ML("water_ml", "Eau bue", "EAU", Format.WATER, "water_goal_ml", null, 1250.0f, 2000.0f, R.drawable.ic_m_drop),
    FOOD_KCAL("food_kcal", "Calories consommées", "REPAS", Format.INT, "food_kcal_goal", null, 1450.0f, 2200.0f, R.drawable.ic_m_food),
    HR_LAST("hr_last", "Fréquence cardiaque (dernière)", "BPM", Format.INT, null, 200.0f, 68.0f, null, R.drawable.ic_m_heart),
    HR_MIN("hr_min", "Fréquence cardiaque min du jour", "FC MIN", Format.INT, null, 200.0f, 52.0f, null, R.drawable.ic_m_heart),
    HR_MAX("hr_max", "Fréquence cardiaque max du jour", "FC MAX", Format.INT, null, 200.0f, 141.0f, null, R.drawable.ic_m_heart),
    SPO2("spo2", "Oxygène dans le sang", "SpO2", Format.PERCENT, null, 100.0f, 96.0f, null, R.drawable.ic_m_drop_o),
    SKIN_TEMP("skin_temp", "Température cutanée", "PEAU", Format.TEMP, null, null, 33.4f, null, R.drawable.ic_m_thermo),
    BODY_TEMP("body_temp", "Température corporelle", "TEMP.", Format.TEMP, null, null, 36.8f, null, R.drawable.ic_m_thermo),
    BP_SYS("bp_sys", "Tension artérielle", "TENSION", Format.PRESSURE, null, null, 121.0f, null, R.drawable.ic_m_heart_pulse),
    GLUCOSE("glucose", "Glycémie", "GLYCÉMIE", Format.DEC1, null, null, 5.4f, null, R.drawable.ic_m_drop),
    WEIGHT("weight", "Poids", "POIDS", Format.KG, null, null, 78.4f, null, R.drawable.ic_m_scale),
    BODY_FAT("body_fat", "Masse grasse", "M. GRASSE", Format.PERCENT, null, 100.0f, 21.5f, null, R.drawable.ic_m_person),
    MUSCLE("muscle", "Masse musculaire squelettique", "MUSCLE", Format.KG, null, null, 34.2f, null, R.drawable.ic_m_person),
    BMI("bmi", "IMC", "IMC", Format.DEC1, null, null, 24.1f, null, R.drawable.ic_m_person),
    VO2MAX("vo2max", "VO2 max (dernière séance)", "VO2 MAX", Format.DEC1, null, null, 44.7f, null, R.drawable.ic_m_runner),
    LAST_EX_MIN("last_ex_min", "Dernière séance : durée", "SÉANCE", Format.DURATION, null, null, 42.0f, null, R.drawable.ic_m_runner),
    LAST_EX_M("last_ex_m", "Dernière séance : distance", "SÉANCE", Format.DISTANCE, null, null, 8120.0f, null, R.drawable.ic_m_runner);
}
