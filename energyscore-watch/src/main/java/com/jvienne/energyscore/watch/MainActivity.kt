package com.jvienne.energyscore.watch

import android.app.Activity
import android.os.Bundle
import android.text.format.DateFormat
import android.view.Gravity
import android.widget.ScrollView
import android.widget.TextView

/**
 * Écran de contrôle de la montre : dernières valeurs reçues du téléphone. Les données
 * s'affichent surtout en complications ; cet écran sert à vérifier la synchronisation.
 */
class MainActivity : Activity() {

    override fun onResume() {
        super.onResume()
        val ts = HealthStore.lastUpdate(this)
        val header = if (ts == 0L) {
            "Santé Sync\n\nRien reçu du téléphone.\nOuvrez Santé Sync sur le téléphone et touchez « Autoriser et synchroniser »."
        } else {
            "Santé Sync\nReçu à ${DateFormat.getTimeFormat(this).format(ts)}"
        }
        val lines = Metric.values().mapNotNull { m ->
            HealthStore.get(this, m.key)?.let { v ->
                val extra = if (m.format == Format.PRESSURE) HealthStore.get(this, "bp_dia") else null
                "${m.label} : ${m.format.text(v, extra)}"
            }
        }
        val text = TextView(this).apply {
            this.text = (listOf(header, "") + lines).joinToString("\n")
            textSize = 14f
            gravity = Gravity.CENTER_HORIZONTAL
            // marges larges : écran rond
            setPadding(48, 56, 48, 72)
        }
        setContentView(ScrollView(this).apply { addView(text) })
    }
}
