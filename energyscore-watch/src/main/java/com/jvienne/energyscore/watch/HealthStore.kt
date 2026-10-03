package com.jvienne.energyscore.watch

import android.content.Context
import java.time.LocalDate

/**
 * Valeurs en cache sur la montre, de deux sources :
 *  - le téléphone (Samsung Health, toutes les 30 min) : instantané complet qui remplace le
 *    précédent ;
 *  - la montre elle-même (Health Services, en direct) : pas, distance, calories, étages du
 *    jour. Elles priment sur celles du téléphone tant qu'elles datent d'aujourd'hui.
 */
object HealthStore {
    private const val PREFS = "sante"
    private const val PREFS_LOCAL = "sante_montre"
    private const val KEY_TS = "ts"
    private const val KEY_DAY = "jour"

    fun replaceAll(context: Context, values: Map<String, Float>, timestampMillis: Long) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().apply {
            clear()
            values.forEach { (k, v) -> putFloat(k, v) }
            putLong(KEY_TS, timestampMillis)
        }.apply()
    }

    /** Valeurs du jour mesurées par la montre (Health Services). */
    fun putLocal(context: Context, values: Map<String, Float>) {
        val prefs = context.getSharedPreferences(PREFS_LOCAL, Context.MODE_PRIVATE)
        val today = LocalDate.now().toString()
        prefs.edit().apply {
            if (prefs.getString(KEY_DAY, null) != today) clear()   // nouveau jour : on repart de zéro
            putString(KEY_DAY, today)
            values.forEach { (k, v) -> putFloat(k, v) }
        }.apply()
    }

    /** Heure de la dernière réception du téléphone (ms), 0 si rien reçu. */
    fun lastUpdate(context: Context): Long =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong(KEY_TS, 0L)

    /** Valeur à afficher : mesure de la montre du jour si elle existe, sinon celle du téléphone. */
    fun get(context: Context, key: String): Float? {
        val local = context.getSharedPreferences(PREFS_LOCAL, Context.MODE_PRIVATE)
        if (local.getString(KEY_DAY, null) == LocalDate.now().toString() && local.contains(key)) {
            return local.getFloat(key, 0f)
        }
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return if (prefs.contains(key)) prefs.getFloat(key, 0f) else null
    }
}
