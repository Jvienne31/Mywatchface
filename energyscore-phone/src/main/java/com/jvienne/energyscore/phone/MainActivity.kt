package com.jvienne.energyscore.phone

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.samsung.android.sdk.health.data.error.ResolvablePlatformException
import kotlinx.coroutines.launch
import java.text.DateFormat
import java.util.Date

/**
 * Écran unique : autorise la lecture Samsung Health, synchronise vers la montre et affiche
 * ce qui a été envoyé. Ensuite la synchronisation se fait seule toutes les 30 minutes.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var valuesText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        statusText = findViewById(R.id.statusText)
        valuesText = findViewById(R.id.valuesText)
        findViewById<Button>(R.id.syncButton).setOnClickListener { syncNow() }
        SyncWorker.schedule(this)
        syncNow()
    }

    private fun syncNow() {
        lifecycleScope.launch {
            statusText.text = getString(R.string.status_running)
            try {
                val reader = HealthReader(this@MainActivity)
                var granted = reader.grantedPermissions()
                if (granted.size < HealthReader.PERMISSIONS.size) {
                    granted = reader.requestPermissions(this@MainActivity)
                }
                if (granted.isEmpty()) {
                    statusText.text = getString(R.string.status_permission_needed)
                    return@launch
                }
                val values = WatchSync.run(this@MainActivity)
                statusText.text = getString(
                    R.string.status_synced, values.size,
                    DateFormat.getTimeInstance(DateFormat.SHORT).format(Date(WatchSync.lastSyncMillis(this@MainActivity))),
                )
                valuesText.text = Keys.LABELS.entries.joinToString("\n") { (key, label) ->
                    "$label : ${values[key]?.let { "%.1f".format(it).removeSuffix(",0").removeSuffix(".0") } ?: "—"}"
                }
            } catch (e: ResolvablePlatformException) {
                // Samsung Health absent, trop ancien ou mode développeur à activer
                statusText.text = getString(R.string.status_error, e.errorMessage ?: e.toString())
                if (e.hasResolution) e.resolve(this@MainActivity)
            } catch (e: Exception) {
                statusText.text = getString(R.string.status_error, e.message ?: e.toString())
            }
        }
    }
}
