package com.jvienne.energyscore.watch

import android.content.Context

/**
 * Dernières valeurs reçues du téléphone, en cache sur la montre : les complications
 * répondent instantanément, sans réseau. Chaque envoi du téléphone est un instantané
 * complet, qui remplace le précédent.
 */
object HealthStore {
    private const val PREFS = "sante"
    private const val KEY_TS = "ts"

    fun replaceAll(context: Context, values: Map<String, Float>, timestampMillis: Long) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().apply {
            clear()
            values.forEach { (k, v) -> putFloat(k, v) }
            putLong(KEY_TS, timestampMillis)
        }.apply()
    }

    /** Heure de la dernière réception (ms), 0 si rien reçu. */
    fun lastUpdate(context: Context): Long =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong(KEY_TS, 0L)

    /** Valeur en cache, ou null si le téléphone ne l'a pas (encore) envoyée. */
    fun get(context: Context, key: String): Float? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return if (prefs.contains(key)) prefs.getFloat(key, 0f) else null
    }
}
