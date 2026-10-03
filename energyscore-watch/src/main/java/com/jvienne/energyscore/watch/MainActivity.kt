package com.jvienne.energyscore.watch

import android.app.Activity
import android.os.Bundle
import android.text.format.DateFormat
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * Écran de contrôle de la montre : dernières valeurs reçues du téléphone, et un essai de
 * lecture directe de Samsung Health sur la montre (voir [DirectReadTest]).
 */
class MainActivity : Activity() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private lateinit var received: TextView
    private lateinit var testResult: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        received = text(14f)
        testResult = text(13f)
        val button = Button(this).apply {
            text = "Test lecture directe"
            setOnClickListener { runTest() }
        }
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(40, 56, 40, 80)   // marges larges : écran rond
            addView(received)
            addView(button)
            addView(testResult)
        }
        setContentView(ScrollView(this).apply { addView(column) })
    }

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
        received.text = (listOf(header, "") + lines + "").joinToString("\n")
    }

    private fun runTest() {
        testResult.text = "Essai en cours…"
        scope.launch { testResult.text = DirectReadTest.run(this@MainActivity) }
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    private fun text(size: Float) = TextView(this).apply {
        textSize = size
        gravity = Gravity.CENTER_HORIZONTAL
    }
}
