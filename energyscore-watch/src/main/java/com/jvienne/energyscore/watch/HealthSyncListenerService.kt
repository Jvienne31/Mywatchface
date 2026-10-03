package com.jvienne.energyscore.watch

import com.google.android.gms.wearable.DataEvent
import com.google.android.gms.wearable.DataEventBuffer
import com.google.android.gms.wearable.DataMapItem
import com.google.android.gms.wearable.WearableListenerService

private const val PATH = "/sante"
private const val KEY_TS = "ts"

/**
 * Reçoit l'instantané Samsung Health poussé par l'appli téléphone (Data Layer, chemin
 * "/sante"), le met en cache, puis fait rafraîchir toutes les complications tout de suite.
 *
 * Le Data Layer ne relie que deux applis de même identifiant et de même signature : le
 * téléphone et la montre partagent donc applicationId et clé (voir build.gradle).
 */
class HealthSyncListenerService : WearableListenerService() {

    override fun onDataChanged(dataEvents: DataEventBuffer) {
        var updated = false
        for (event in dataEvents) {
            if (event.type != DataEvent.TYPE_CHANGED || event.dataItem.uri.path != PATH) continue
            val map = DataMapItem.fromDataItem(event.dataItem).dataMap
            val values = map.keySet().filter { it != KEY_TS }.associateWith { map.getFloat(it) }
            HealthStore.replaceAll(applicationContext, values, map.getLong(KEY_TS, System.currentTimeMillis()))
            updated = true
        }
        if (!updated) return
        PassiveDataService.register(applicationContext)   // entretient l'écoute en direct
        PassiveDataService.requestUpdate(applicationContext, ALL_PROVIDERS)
        SanteTileService.refresh(applicationContext)
    }
}
