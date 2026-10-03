package com.jvienne.energyscore.phone

import android.content.Context
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.tasks.await

/**
 * Lit Samsung Health et pousse l'instantané vers la montre (Data Layer, chemin [Keys.PATH]).
 * L'appli montre (energyscore-watch) le met en cache et le sert en complications.
 */
object WatchSync {
    private const val PREFS = "derniere_synchro"

    suspend fun run(context: Context): Map<String, Float> {
        val values = HealthReader(context).readAll()
        val request = PutDataMapRequest.create(Keys.PATH).apply {
            values.forEach { (k, v) -> dataMap.putFloat(k, v) }
            dataMap.putLong(Keys.TIMESTAMP, System.currentTimeMillis())   // force la livraison
        }.asPutDataRequest().setUrgent()
        Wearable.getDataClient(context).putDataItem(request).await()
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().apply {
            clear()   // instantané complet : une donnée disparue ne doit pas rester affichée
            values.forEach { (k, v) -> putFloat(k, v) }
            putLong("ts", System.currentTimeMillis())
        }.apply()
        return values
    }

    /** Dernières valeurs envoyées (affichées au lancement, avant la synchronisation). */
    fun lastValues(context: Context): Map<String, Float> =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).all
            .filter { it.key != "ts" && it.value is Float }
            .mapValues { it.value as Float }

    fun lastSyncMillis(context: Context): Long =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong("ts", 0L)
}
