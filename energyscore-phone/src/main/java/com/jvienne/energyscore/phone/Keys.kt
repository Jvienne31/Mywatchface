// FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py : ne pas éditer à la main.

package com.jvienne.energyscore.phone

/** Clés des valeurs envoyées à la montre (chemin Data Layer [PATH]). */
object Keys {
    const val PATH = "/sante"
    const val TIMESTAMP = "ts"
    const val ENERGY = "energy"
    const val SLEEP_SCORE = "sleep_score"
    const val SLEEP_MIN = "sleep_min"
    const val STEPS = "steps"
    const val DISTANCE_M = "distance_m"
    const val ACTIVE_KCAL = "active_kcal"
    const val TOTAL_KCAL = "total_kcal"
    const val ACTIVE_MIN = "active_min"
    const val FLOORS = "floors"
    const val WATER_ML = "water_ml"
    const val FOOD_KCAL = "food_kcal"
    const val HR_LAST = "hr_last"
    const val HR_MIN = "hr_min"
    const val HR_MAX = "hr_max"
    const val SPO2 = "spo2"
    const val SKIN_TEMP = "skin_temp"
    const val BODY_TEMP = "body_temp"
    const val BP_SYS = "bp_sys"
    const val GLUCOSE = "glucose"
    const val WEIGHT = "weight"
    const val BODY_FAT = "body_fat"
    const val MUSCLE = "muscle"
    const val BMI = "bmi"
    const val VO2MAX = "vo2max"
    const val LAST_EX_MIN = "last_ex_min"
    const val LAST_EX_M = "last_ex_m"
    const val SLEEP_GOAL_MIN = "sleep_goal_min"
    const val STEPS_GOAL = "steps_goal"
    const val ACTIVE_KCAL_GOAL = "active_kcal_goal"
    const val ACTIVE_MIN_GOAL = "active_min_goal"
    const val WATER_GOAL_ML = "water_goal_ml"
    const val FOOD_KCAL_GOAL = "food_kcal_goal"
    const val BP_DIA = "bp_dia"

    /** Libellés affichés dans l'appli téléphone (même ordre que sur la montre). */
    val LABELS = linkedMapOf(
        ENERGY to "Score d'énergie",
        SLEEP_SCORE to "Score de sommeil",
        SLEEP_MIN to "Durée de sommeil",
        STEPS to "Pas (objectif)",
        DISTANCE_M to "Distance du jour",
        ACTIVE_KCAL to "Calories actives",
        TOTAL_KCAL to "Calories totales",
        ACTIVE_MIN to "Temps actif",
        FLOORS to "Étages",
        WATER_ML to "Eau bue",
        FOOD_KCAL to "Calories consommées",
        HR_LAST to "Fréquence cardiaque (dernière)",
        HR_MIN to "Fréquence cardiaque min du jour",
        HR_MAX to "Fréquence cardiaque max du jour",
        SPO2 to "Oxygène dans le sang",
        SKIN_TEMP to "Température cutanée",
        BODY_TEMP to "Température corporelle",
        BP_SYS to "Tension artérielle",
        GLUCOSE to "Glycémie",
        WEIGHT to "Poids",
        BODY_FAT to "Masse grasse",
        MUSCLE to "Masse musculaire squelettique",
        BMI to "IMC",
        VO2MAX to "VO2 max (dernière séance)",
        LAST_EX_MIN to "Dernière séance : durée",
        LAST_EX_M to "Dernière séance : distance",
    )
}
