package com.jvienne.energyscore.phone

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.launch

// --- Samsung Health Data SDK -------------------------------------------------------------
// ATTENTION : les imports et appels ci-dessous suivent le nommage documenté publiquement
// (com.samsung.android.sdk.health.data.*, DataType.EnergyScoreType, HealthDataService,
// PermissionManager) mais n'ont PAS pu être vérifiés contre le javadoc exact du SDK : le site
// developer.samsung.com est inaccessible depuis cet environnement. Le SDK (fichier .aar) n'est
// de toute façon pas encore présent dans libs/, donc ce fichier ne compilera pas tel quel.
//
// Étape suivante une fois le SDK téléchargé (voir README à la racine du dépôt) : ouvrir le
// projet d'exemple fourni dans le zip du SDK ("Hello SDK"), comparer son code de lecture
// EnergyScoreType avec le bloc readEnergyScore() ci-dessous, et corriger les noms d'appels si
// besoin — la structure autour (permission, callback, envoi au Data Layer) restera identique.
//
// import com.samsung.android.sdk.health.data.HealthDataService
// import com.samsung.android.sdk.health.data.HealthDataStore
// import com.samsung.android.sdk.health.data.permission.AccessType
// import com.samsung.android.sdk.health.data.permission.Permission
// import com.samsung.android.sdk.health.data.request.DataType
// import com.samsung.android.sdk.health.data.request.LocalTimeFilter
// -------------------------------------------------------------------------------------------

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

    /**
     * Lit le dernier score d'énergie connu via le Samsung Health Data SDK (mode développeur,
     * lecture seule, pas besoin de partenariat Samsung pour un usage personnel non distribué).
     *
     * TODO(à finaliser avec le SDK réel — voir le bloc de commentaires en tête de fichier) :
     *   1. store = HealthDataService.getStore(applicationContext)
     *   2. demander la permission de lecture sur DataType.EnergyScoreType si pas déjà accordée
     *   3. construire une requête de lecture sur la période "aujourd'hui" (LocalTimeFilter)
     *   4. renvoyer la valeur la plus récente (0–100), ou null si aucune donnée / permission refusée
     */
    private suspend fun readEnergyScore(): Int? {
        // Squelette temporaire tant que le .aar n'est pas intégré : à remplacer par le vrai
        // appel SDK. Laissé explicite (et non un simple retour statique) pour que l'échec soit
        // visible immédiatement plutôt que de faire croire à une synchronisation réussie.
        throw NotImplementedError(
            "Samsung Health Data SDK non encore intégré : voir libs/README et le bloc de " +
                "commentaires en tête de ce fichier."
        )
    }

    private fun pushToWatch(score: Int) {
        val request = PutDataMapRequest.create("/energy_score").apply {
            dataMap.putInt("score", score)
            dataMap.putLong("timestamp", System.currentTimeMillis())
        }.asPutDataRequest().setUrgent()

        Wearable.getDataClient(this).putDataItem(request)
    }
}
