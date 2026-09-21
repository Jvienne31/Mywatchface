package com.jvienne.energyscore.phone

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable
import com.samsung.android.sdk.health.data.HealthDataService
import com.samsung.android.sdk.health.data.permission.AccessType
import com.samsung.android.sdk.health.data.permission.Permission
import com.samsung.android.sdk.health.data.request.DataType
import com.samsung.android.sdk.health.data.request.LocalTimeFilter
import com.samsung.android.sdk.health.data.request.Ordering
import kotlinx.coroutines.launch
import java.time.LocalDate

/**
 * Lit le score d'énergie Samsung Health (Samsung Health Data SDK, mode développeur — pas besoin
 * d'accord partenaire pour un usage personnel non distribué) et le pousse vers la montre via le
 * Data Layer Wear OS, où `energyscore-watch` l'expose comme un vrai fournisseur de complication.
 *
 * Ce fichier suit le pattern officiel confirmé pour la lecture d'un type de donnée instantané
 * (ex. HeartRateType) :
 *   val store = HealthDataService.getStore(context)
 *   val request = DataType.<Type>.readDataRequestBuilder.setLocalTimeFilter(filter)....build()
 *   val list = store.readData(request).dataList
 *
 * Deux points précis restent à confirmer dans Android Studio une fois le .aar en place (autocomplete
 * règle ça en quelques secondes, voir energyscore-phone/libs/README.md) :
 *   - le nom exact du champ de valeur sur EnergyScoreType (ici DataType.EnergyScoreType.SCORE) ;
 *   - si `requestPermissions` doit être appelée directement ou via un callback d'activité —
 *     ici elle est traitée comme suspend, cohérent avec le reste d'un SDK conçu pour coroutines.
 * Tout le reste (permission, filtre temporel, lecture, envoi à la montre) est le vrai appel SDK.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        findViewById<Button>(R.id.syncButton).setOnClickListener { syncNow() }

        syncNow()
    }

    private fun syncNow() {
        lifecycleScope.launch {
            try {
                val score = readEnergyScore()
                if (score == null) {
                    statusText.text = getString(R.string.status_permission_needed)
                    return@launch
                }
                pushToWatch(score)
                statusText.text = getString(R.string.status_synced, score)
            } catch (e: Exception) {
                statusText.text = getString(R.string.status_error, e.message ?: e.toString())
            }
        }
    }

    private suspend fun readEnergyScore(): Int? {
        val store = HealthDataService.getStore(applicationContext)

        val permissions = setOf(Permission.of(DataType.EnergyScoreType, AccessType.READ))
        var granted = store.getGrantedPermissions(permissions)
        if (!granted.containsAll(permissions)) {
            store.requestPermissions(permissions, this@MainActivity)
            granted = store.getGrantedPermissions(permissions)
        }
        if (!granted.containsAll(permissions)) {
            return null
        }

        val today = LocalDate.now()
        val filter = LocalTimeFilter.of(today.atStartOfDay(), today.plusDays(1).atStartOfDay())
        val readRequest = DataType.EnergyScoreType.readDataRequestBuilder
            .setLocalTimeFilter(filter)
            .setOrdering(Ordering.DESC)
            .build()

        val dataList = store.readData(readRequest).dataList
        val latest = dataList.firstOrNull() ?: return null

        // TODO : confirmer le nom du champ dans le javadoc du SDK une fois téléchargé
        // (probablement DataType.EnergyScoreType.SCORE — cf. commentaire en tête de fichier).
        val score = latest.getValue(DataType.EnergyScoreType.SCORE) ?: return null
        return score.toInt().coerceIn(0, 100)
    }

    private fun pushToWatch(score: Int) {
        val request = PutDataMapRequest.create("/energy_score").apply {
            dataMap.putInt("score", score)
            dataMap.putLong("timestamp", System.currentTimeMillis())
        }.asPutDataRequest().setUrgent()

        Wearable.getDataClient(this).putDataItem(request)
    }
}
