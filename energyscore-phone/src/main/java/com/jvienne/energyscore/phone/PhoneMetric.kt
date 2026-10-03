// FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py : ne pas éditer à la main.

package com.jvienne.energyscore.phone

/** Données affichées par l'appli téléphone (même table que les complications). */
enum class PhoneMetric(
    val key: String,
    val label: String,
    val title: String,
    val format: Format,
    val goalKey: String?,
    val max: Float?,
    val icon: Int,
) {
    ENERGY("energy", "Score d'énergie", "ÉNERGIE", Format.INT, null, 100.0f, R.drawable.ic_m_bolt),
    SLEEP_SCORE("sleep_score", "Score de sommeil", "SOMMEIL", Format.INT, null, 100.0f, R.drawable.ic_m_moon_star),
    SLEEP_MIN("sleep_min", "Durée de sommeil", "SOMMEIL", Format.DURATION, "sleep_goal_min", null, R.drawable.ic_m_moon),
    STEPS("steps", "Pas (objectif)", "PAS", Format.INT, "steps_goal", null, R.drawable.ic_m_steps),
    DISTANCE_M("distance_m", "Distance du jour", "DISTANCE", Format.DISTANCE, null, null, R.drawable.ic_m_pin),
    ACTIVE_KCAL("active_kcal", "Calories actives", "KCAL ACT.", Format.INT, "active_kcal_goal", null, R.drawable.ic_m_flame),
    TOTAL_KCAL("total_kcal", "Calories totales", "KCAL", Format.INT, null, null, R.drawable.ic_m_flame),
    ACTIVE_MIN("active_min", "Temps actif", "ACTIF", Format.DURATION, "active_min_goal", null, R.drawable.ic_m_timer),
    FLOORS("floors", "Étages", "ÉTAGES", Format.INT, null, null, R.drawable.ic_m_stairs),
    WATER_ML("water_ml", "Eau bue", "EAU", Format.WATER, "water_goal_ml", null, R.drawable.ic_m_drop),
    FOOD_KCAL("food_kcal", "Calories consommées", "REPAS", Format.INT, "food_kcal_goal", null, R.drawable.ic_m_food),
    HR_LAST("hr_last", "Fréquence cardiaque (dernière)", "BPM", Format.INT, null, 200.0f, R.drawable.ic_m_heart),
    HR_MIN("hr_min", "Fréquence cardiaque min du jour", "FC MIN", Format.INT, null, 200.0f, R.drawable.ic_m_heart),
    HR_MAX("hr_max", "Fréquence cardiaque max du jour", "FC MAX", Format.INT, null, 200.0f, R.drawable.ic_m_heart),
    SPO2("spo2", "Oxygène dans le sang", "SpO2", Format.PERCENT, null, 100.0f, R.drawable.ic_m_drop_o),
    SKIN_TEMP("skin_temp", "Température cutanée", "PEAU", Format.TEMP, null, null, R.drawable.ic_m_thermo),
    BODY_TEMP("body_temp", "Température corporelle", "TEMP.", Format.TEMP, null, null, R.drawable.ic_m_thermo),
    BP_SYS("bp_sys", "Tension artérielle", "TENSION", Format.PRESSURE, null, null, R.drawable.ic_m_heart_pulse),
    GLUCOSE("glucose", "Glycémie", "GLYCÉMIE", Format.DEC1, null, null, R.drawable.ic_m_drop),
    WEIGHT("weight", "Poids", "POIDS", Format.KG, null, null, R.drawable.ic_m_scale),
    BODY_FAT("body_fat", "Masse grasse", "M. GRASSE", Format.PERCENT, null, 100.0f, R.drawable.ic_m_person),
    MUSCLE("muscle", "Masse musculaire squelettique", "MUSCLE", Format.KG, null, null, R.drawable.ic_m_person),
    BMI("bmi", "IMC", "IMC", Format.DEC1, null, null, R.drawable.ic_m_person),
    VO2MAX("vo2max", "VO2 max (dernière séance)", "VO2 MAX", Format.DEC1, null, null, R.drawable.ic_m_runner),
    LAST_EX_MIN("last_ex_min", "Dernière séance : durée", "SÉANCE", Format.DURATION, null, null, R.drawable.ic_m_runner),
    LAST_EX_M("last_ex_m", "Dernière séance : distance", "SÉANCE", Format.DISTANCE, null, null, R.drawable.ic_m_runner);
}
