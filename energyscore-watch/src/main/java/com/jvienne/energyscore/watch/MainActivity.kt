package com.jvienne.energyscore.watch

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.os.Bundle
import android.text.format.DateFormat
import android.view.Gravity
import android.widget.ScrollView
import android.widget.TextView

/**
 * Écran de contrôle de la montre : valeurs disponibles pour les complications. Demande aussi
 * l'autorisation « activité physique » pour les mesures en direct (Health Services).
 */
class MainActivity : Activity() {

    private lateinit var info: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        info = TextView(this).apply {
            textSize = 14f
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(40, 56, 40, 80)   // marges larges : écran rond
        }
        setContentView(ScrollView(this).apply { addView(info) })
        if (checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.ACTIVITY_RECOGNITION), 1)
        } else {
            PassiveDataService.register(this)
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        PassiveDataService.register(this)
        refresh()
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        val ts = HealthStore.lastUpdate(this)
        val phone = if (ts == 0L) {
            "Téléphone : rien reçu.\nOuvrez Santé Sync sur le téléphone."
        } else {
            "Téléphone : reçu à ${DateFormat.getTimeFormat(this).format(ts)}"
        }
        val live = if (checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION) == PackageManager.PERMISSION_GRANTED) {
            "Montre : pas, distance, calories, étages en direct"
        } else {
            "Montre : autorisation « activité physique » refusée (mesures en direct désactivées)"
        }
        val lines = Metric.values().mapNotNull { m ->
            HealthStore.get(this, m.key)?.let { v ->
                val extra = if (m.format == Format.PRESSURE) HealthStore.get(this, "bp_dia") else null
                "${m.label} : ${m.format.text(v, extra)}"
            }
        }
        info.text = (listOf("Santé Sync", phone, live, "") + lines).joinToString("\n")
    }
}
