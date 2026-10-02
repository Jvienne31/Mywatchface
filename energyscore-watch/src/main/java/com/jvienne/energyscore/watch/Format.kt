package com.jvienne.energyscore.watch

import java.util.Locale
import kotlin.math.roundToInt

/** Mise en forme courte des valeurs (elles doivent tenir dans un dôme de Prisme). */
enum class Format {
    INT, PERCENT, DURATION, DISTANCE, WATER, TEMP, DEC1, KG, PRESSURE;

    /** extra : seconde valeur (diastolique pour la tension). */
    fun text(v: Float, extra: Float?): String = when (this) {
        INT -> v.roundToInt().toString()
        PERCENT -> "${v.roundToInt()}%"
        DURATION -> v.roundToInt().let { m -> if (m >= 60) "%dh%02d".format(m / 60, m % 60) else "$m min" }
        DISTANCE -> if (v >= 1000f) fr("%.1f km", v / 1000f) else "${v.roundToInt()} m"
        WATER -> if (v >= 1000f) fr("%.1f L", v / 1000f) else "${v.roundToInt()} ml"
        TEMP -> fr("%.1f°", v)
        DEC1 -> fr("%.1f", v)
        KG -> fr("%.1f kg", v)
        PRESSURE -> if (extra != null) "${v.roundToInt()}/${extra.roundToInt()}" else v.roundToInt().toString()
    }

    private fun fr(pattern: String, v: Float) = String.format(Locale.FRANCE, pattern, v)
}
