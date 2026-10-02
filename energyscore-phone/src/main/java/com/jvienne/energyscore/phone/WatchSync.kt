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
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putLong("ts", System.currentTimeMillis()).apply()
        return values
    }

    fun lastSyncMillis(context: Context): Long =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong("ts", 0L)
}
