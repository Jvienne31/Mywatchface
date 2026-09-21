package com.jvienne.energyscore.watch

import android.content.ComponentName
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester
import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.WearableListenerService

private const val PATH = "/energy_score"
private const val KEY_SCORE = "score"
private const val KEY_TIMESTAMP = "timestamp"

/**
 * Écoute les mises à jour poussées par l'appli téléphone (`energyscore-phone`) sur le chemin
 * Data Layer "/energy_score", met à jour le cache local, puis force la complication à se
 * rafraîchir immédiatement plutôt que d'attendre le prochain cycle système.
 */
class EnergyScoreSyncListenerService : WearableListenerService() {

    override fun onDataChanged(dataEvents: DataEventBuffer) {
        var latestScore: Int? = null

        for (event in dataEvents) {
            if (event.type != DataEvent.TYPE_CHANGED) continue
            val item = event.dataItem
            if (item.uri.path != PATH) continue

            val map = DataMapItem.fromDataItem(item).dataMap
            if (map.containsKey(KEY_SCORE)) {
                latestScore = map.getInt(KEY_SCORE)
                val timestamp = if (map.containsKey(KEY_TIMESTAMP)) map.getLong(KEY_TIMESTAMP) else System.currentTimeMillis()
                EnergyScoreStore.save(applicationContext, latestScore, timestamp)
            }
        }

        if (latestScore != null) {
            ComplicationDataSourceUpdateRequester.create(
                context = applicationContext,
                complicationDataSourceComponent = ComponentName(
                    applicationContext,
                    EnergyScoreComplicationService::class.java
                )
            ).requestUpdateAll()
        }
    }
}
