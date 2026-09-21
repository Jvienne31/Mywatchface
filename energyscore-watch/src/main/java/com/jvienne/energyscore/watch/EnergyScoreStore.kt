package com.jvienne.energyscore.watch

import android.content.Context

/**
 * Dernier score d'énergie reçu du téléphone (0-100), mis en cache localement sur la montre
 * pour que le fournisseur de complication puisse répondre instantanément sans réseau.
 */
object EnergyScoreStore {
    private const val PREFS = "energy_score_prefs"
    private const val KEY_SCORE = "score"
    private const val KEY_TIMESTAMP = "timestamp"

    fun save(context: Context, score: Int, timestampMillis: Long) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putInt(KEY_SCORE, score.coerceIn(0, 100))
            .putLong(KEY_TIMESTAMP, timestampMillis)
            .apply()
    }

    /** Retourne le score en cache, ou null si aucune synchronisation n'a encore eu lieu. */
    fun read(context: Context): Int? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return if (prefs.contains(KEY_SCORE)) prefs.getInt(KEY_SCORE, 0) else null
    }

    fun lastUpdateMillis(context: Context): Long {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong(KEY_TIMESTAMP, 0L)
    }
}
