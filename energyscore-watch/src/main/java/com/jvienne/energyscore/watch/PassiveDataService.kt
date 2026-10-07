package com.jvienne.energyscore.watch

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.health.services.client.HealthServices
import androidx.health.services.client.PassiveListenerService
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.PassiveListenerConfig
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester

/**
 * Valeurs du jour mesurées par la montre elle-même (Health Services, mode passif) : pas,
 * distance, calories, étages. Mises à jour en direct, même téléphone éteint ; elles priment sur
 * celles du téléphone (voir [HealthStore.get]).
 */
class PassiveDataService : PassiveListenerService() {

    override fun onNewDataPointsReceived(dataPoints: DataPointContainer) {
        val values = mutableMapOf<String, Float>()
        dataPoints.getData(DataType.STEPS_DAILY).lastOrNull()?.let { values["steps"] = it.value.toFloat() }
        dataPoints.getData(DataType.DISTANCE_DAILY).lastOrNull()?.let { values["distance_m"] = it.value.toFloat() }
        dataPoints.getData(DataType.CALORIES_DAILY).lastOrNull()?.let { values["total_kcal"] = it.value.toFloat() }
        dataPoints.getData(DataType.FLOORS_DAILY).lastOrNull()?.let { values["floors"] = it.value.toFloat() }
        if (values.isEmpty()) return
        HealthStore.putLocal(applicationContext, values)
        // Économie de batterie : les pas arrivent très souvent ; on ne fait redessiner
        // complications et tuile qu'au plus toutes les 5 minutes (les valeurs, elles, sont
        // toujours enregistrées et servies à la prochaine mise à jour).
        val prefs = applicationContext.getSharedPreferences("sante_montre_maj", MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (now - prefs.getLong("derniere", 0L) < MIN_INTERVAL_MS) return
        prefs.edit().putLong("derniere", now).apply()
        requestUpdate(applicationContext, LOCAL_PROVIDERS)
        SanteTileService.refresh(applicationContext)
    }

    companion object {
        private const val MIN_INTERVAL_MS = 5 * 60 * 1000L

        private val LOCAL_PROVIDERS = listOf(
            StepsProvider::class.java, DistanceMProvider::class.java,
            TotalKcalProvider::class.java, FloorsProvider::class.java,
        )

        /** (Ré)inscrit l'écoute passive ; sans effet tant que l'autorisation manque. */
        fun register(context: Context) {
            if (context.checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION) !=
                PackageManager.PERMISSION_GRANTED
            ) return
            try {
                val config = PassiveListenerConfig.builder()
                    .setDataTypes(setOf(DataType.STEPS_DAILY, DataType.DISTANCE_DAILY,
                        DataType.CALORIES_DAILY, DataType.FLOORS_DAILY))
                    .build()
                HealthServices.getClient(context).passiveMonitoringClient
                    .setPassiveListenerServiceAsync(PassiveDataService::class.java, config)
            } catch (e: Exception) {
                Log.w("PassiveDataService", "Inscription Health Services impossible", e)
            }
        }

        fun requestUpdate(context: Context, providers: List<Class<out MetricComplicationService>>) {
            for (provider in providers) {
                ComplicationDataSourceUpdateRequester.create(
                    context = context,
                    complicationDataSourceComponent = ComponentName(context, provider),
                ).requestUpdateAll()
            }
        }
    }
}
