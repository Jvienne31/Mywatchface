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
        requestUpdate(applicationContext, LOCAL_PROVIDERS)
    }

    companion object {
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
