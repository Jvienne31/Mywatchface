package com.jvienne.energyscore.watch

import android.content.Context

/** Couleurs de la palette Lagune de Prisme (ARGB), communes à la tuile et à l'écran. */
object Lagune {
    const val BG = 0xFF0A1729.toInt()
    const val CARD = 0xFF13232E.toInt()
    const val TRACK = 0xFF0E4756.toInt()
    const val BUTTON = 0xFF2A9BA6.toInt()
    const val INK = 0xFFDDEFF0.toInt()
    const val ACCENT = 0xFF7FE3EC.toInt()
    const val SOFT = 0xFF8FB3B8.toInt()
}

/** Une donnée prête à afficher : valeur mise en forme, complément, progression (0-1). */
data class Reading(val metric: Metric, val value: String, val sub: String?, val progress: Float?)

/** Lit une donnée du cache ; null si elle n'a jamais été reçue ni mesurée. */
fun Context.reading(metric: Metric): Reading? {
    val v = HealthStore.get(this, metric.key) ?: return null
    val extra = if (metric.format == Format.PRESSURE) HealthStore.get(this, "bp_dia") else null
    val goal = metric.goalKey?.let { HealthStore.get(this, it) }?.takeIf { it > 0f }
    val sub = when {
        goal != null -> "/ ${metric.format.text(goal, null)}"
        metric.max == 100f && metric.format == Format.INT -> "/ 100"
        else -> null
    }
    val limit = goal ?: metric.max
    val progress = limit?.let { (v / it).coerceIn(0f, 1f) }
    return Reading(metric, metric.format.text(v, extra), sub, progress)
}
