package com.jvienne.energyscore.watch

import android.app.Activity
import com.samsung.android.sdk.health.data.HealthDataService
import com.samsung.android.sdk.health.data.error.HealthDataException
import com.samsung.android.sdk.health.data.error.ResolvablePlatformException
import com.samsung.android.sdk.health.data.permission.AccessType
import com.samsung.android.sdk.health.data.permission.Permission
import com.samsung.android.sdk.health.data.request.DataType
import com.samsung.android.sdk.health.data.request.DataTypes
import com.samsung.android.sdk.health.data.request.LocalDateFilter
import com.samsung.android.sdk.health.data.request.LocalTimeFilter
import com.samsung.android.sdk.health.data.request.Ordering
import java.time.LocalDate
import java.time.LocalDateTime

/**
 * Essai : le Samsung Health Data SDK, documenté pour les téléphones, peut-il lire les scores
 * directement sur la montre (Samsung Health montre : com.samsung.android.wear.shealth, que
 * le SDK déclare dans son manifeste) ? Renvoie un compte rendu lisible, succès ou erreur.
 */
object DirectReadTest {

    suspend fun run(activity: Activity): String = try {
        val store = HealthDataService.getStore(activity)
        val perms = setOf(
            Permission.of(DataTypes.ENERGY_SCORE, AccessType.READ),
            Permission.of(DataTypes.SLEEP, AccessType.READ),
            Permission.of(DataTypes.STEPS, AccessType.READ),
        )
        var granted = store.getGrantedPermissions(perms)
        if (granted.size < perms.size) granted = store.requestPermissions(perms, activity)
        if (granted.isEmpty()) {
            "Connexion OK, mais aucune autorisation accordée."
        } else {
            val today = LocalDate.now()
            val now = LocalDateTime.now()
            val energy = store.readData(
                DataTypes.ENERGY_SCORE.readDataRequestBuilder
                    .setLocalDateFilter(LocalDateFilter.of(today.minusDays(1), today.plusDays(1)))
                    .setOrdering(Ordering.DESC).setLimit(1).build()
            ).dataList.firstOrNull()?.getValue(DataType.EnergyScoreType.ENERGY_SCORE)
            val sleep = store.readData(
                DataTypes.SLEEP.readDataRequestBuilder
                    .setLocalTimeFilter(LocalTimeFilter.of(now.minusDays(2), now))
                    .setOrdering(Ordering.DESC).setLimit(1).build()
            ).dataList.firstOrNull()?.getValue(DataType.SleepType.SLEEP_SCORE)
            val steps = store.aggregateData(
                DataType.StepsType.TOTAL.requestBuilder
                    .setLocalTimeFilter(LocalTimeFilter.of(today.atStartOfDay(), now)).build()
            ).dataList.firstOrNull()?.value
            "LECTURE DIRECTE OK\nÉnergie : ${energy ?: "—"}\nSommeil : ${sleep ?: "—"}\nPas : ${steps ?: "—"}\n" +
                "(${granted.size}/${perms.size} autorisations)"
        }
    } catch (e: ResolvablePlatformException) {
        if (e.hasResolution) e.resolve(activity)
        "Échec (résoluble) : code ${e.errorCode}\n${e.errorMessage}"
    } catch (e: HealthDataException) {
        "Échec SDK : code ${e.errorCode}\n${e.errorMessage}"
    } catch (e: Throwable) {
        "Échec : ${e.javaClass.simpleName}\n${e.message}"
    }
}
