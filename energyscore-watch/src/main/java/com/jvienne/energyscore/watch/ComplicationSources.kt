package com.jvienne.energyscore.watch

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager

/**
 * Sources de complications installées sur la montre (nom affiché, composant, types). Sert à
 * relever le nom exact des sources Samsung Health pour les préréglages de Prisme
 * (DefaultProviderPolicy primaryProvider="paquet/classe"), sans adb.
 */
object ComplicationSources {
    private const val ACTION = "android.support.wearable.complications.ACTION_COMPLICATION_UPDATE_REQUEST"
    private const val TYPES = "android.support.wearable.complications.SUPPORTED_TYPES"

    data class Source(val label: String, val component: String, val types: String)

    fun list(context: Context): List<Source> {
        val pm = context.packageManager
        return pm.queryIntentServices(Intent(ACTION), PackageManager.GET_META_DATA)
            .map { ri ->
                val si = ri.serviceInfo
                Source(
                    label = ri.loadLabel(pm).toString(),
                    component = "${si.packageName}/${si.name}",
                    types = si.metaData?.getString(TYPES).orEmpty(),
                )
            }
            // Samsung Health d'abord, puis les autres par appli
            .sortedWith(compareBy({ !it.component.contains("shealth") }, { it.component }))
    }
}
