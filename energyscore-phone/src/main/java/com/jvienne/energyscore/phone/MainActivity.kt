package com.jvienne.energyscore.phone

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import com.samsung.android.sdk.health.data.error.ResolvablePlatformException
import kotlinx.coroutines.launch
import java.text.DateFormat
import java.util.Date

// Palette Lagune (celle de Prisme et de la tuile montre)
private val Bg = Color(0xFF0A1729)
private val CardBg = Color(0xFF13232E)
private val Track = Color(0xFF0E4756)
private val ButtonBg = Color(0xFF2A9BA6)
private val Ink = Color(0xFFDDEFF0)
private val Accent = Color(0xFF7FE3EC)
private val Soft = Color(0xFF8FB3B8)
private val Alert = Color(0xFFFF8A80)
private val Barlow = FontFamily(
    Font(R.font.barlowcondensed_medium, FontWeight.Medium),
    Font(R.font.barlowcondensed_semibold, FontWeight.SemiBold),
)

/** Données affichées en tête (anneaux et vignettes) ; les autres vont dans la liste. */
private val HEADLINE = setOf(
    PhoneMetric.ENERGY, PhoneMetric.SLEEP_SCORE, PhoneMetric.SLEEP_MIN, PhoneMetric.STEPS, PhoneMetric.DISTANCE_M,
)

/** Une donnée mise en forme : valeur, complément (objectif), progression 0-1. */
private data class Reading(val metric: PhoneMetric, val value: String, val sub: String?, val progress: Float?)

private fun reading(values: Map<String, Float>, m: PhoneMetric): Reading? {
    val v = values[m.key] ?: return null
    val extra = if (m.format == Format.PRESSURE) values[Keys.BP_DIA] else null
    val goal = m.goalKey?.let { values[it] ?: derivedGoal(values, it) }?.takeIf { it > 0f }
    val sub = when {
        goal != null -> "/ ${m.format.text(goal, null)}"
        m.max == 100f && m.format == Format.INT -> "/ 100"
        else -> null
    }
    val progress = (goal ?: m.max)?.let { (v / it).coerceIn(0f, 1f) }
    return Reading(m, m.format.text(v, extra), sub, progress)
}

/** Objectif de distance déduit de l'objectif de pas à la longueur de pas du jour (comme sur la montre). */
private fun derivedGoal(values: Map<String, Float>, key: String): Float? {
    if (key != "distance_goal_m") return null
    val steps = values[Keys.STEPS]?.takeIf { it > 0f } ?: return null
    val distance = values[Keys.DISTANCE_M] ?: return null
    val goal = values[Keys.STEPS_GOAL] ?: return null
    return distance / steps * goal
}

/**
 * Tableau de bord du jour (même esprit que la tuile montre) : autorise la lecture Samsung
 * Health, synchronise vers la montre et affiche ce qui a été envoyé. Ensuite la
 * synchronisation se fait seule toutes les 30 minutes.
 */
class MainActivity : ComponentActivity() {

    private var values by mutableStateOf<Map<String, Float>>(emptyMap())
    private var lastSync by mutableLongStateOf(0L)
    private var status by mutableStateOf<String?>(null)
    private var error by mutableStateOf(false)
    private var busy by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        // Fond sombre : icônes de barre d'état claires, même si le téléphone est en thème clair
        enableEdgeToEdge(SystemBarStyle.dark(android.graphics.Color.TRANSPARENT), SystemBarStyle.dark(android.graphics.Color.TRANSPARENT))
        super.onCreate(savedInstanceState)
        values = WatchSync.lastValues(this)
        lastSync = WatchSync.lastSyncMillis(this)
        setContent {
            Dashboard(values, lastSync, status, error, busy, ::syncNow)
        }
        SyncWorker.schedule(this)
        syncNow()
    }

    private fun syncNow() {
        if (busy) return
        lifecycleScope.launch {
            busy = true
            error = false
            status = getString(R.string.status_running)
            try {
                val reader = HealthReader(this@MainActivity)
                var granted = reader.grantedPermissions()
                if (granted.size < HealthReader.PERMISSIONS.size) {
                    granted = reader.requestPermissions(this@MainActivity)
                }
                if (granted.isEmpty()) {
                    error = true
                    status = getString(R.string.status_permission_needed)
                    return@launch
                }
                values = WatchSync.run(this@MainActivity)
                lastSync = WatchSync.lastSyncMillis(this@MainActivity)
                status = null
            } catch (e: ResolvablePlatformException) {
                // Samsung Health absent, trop ancien ou mode développeur à activer
                error = true
                status = getString(R.string.status_error, e.errorMessage ?: e.toString())
                if (e.hasResolution) e.resolve(this@MainActivity)
            } catch (e: Exception) {
                error = true
                status = getString(R.string.status_error, e.message ?: e.toString())
            } finally {
                busy = false
            }
        }
    }
}

@Composable
private fun Dashboard(
    values: Map<String, Float>,
    lastSync: Long,
    status: String?,
    error: Boolean,
    busy: Boolean,
    onSync: () -> Unit,
) {
    val energy = reading(values, PhoneMetric.ENERGY)
    val sleepScore = reading(values, PhoneMetric.SLEEP_SCORE)
    val others = PhoneMetric.values().filter { it !in HEADLINE }.mapNotNull { reading(values, it) }
    val bars = WindowInsets.systemBars.asPaddingValues()
    LazyColumn(
        modifier = Modifier.fillMaxSize().background(Bg),
        contentPadding = PaddingValues(
            start = 16.dp, end = 16.dp,
            top = bars.calculateTopPadding() + 16.dp, bottom = bars.calculateBottomPadding() + 24.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column {
                Label("Santé Sync", Accent, 32.sp, bold = true)
                val sync = if (lastSync == 0L) "Pas encore synchronisé"
                else "Envoyé à la montre à " + DateFormat.getTimeInstance(DateFormat.SHORT).format(Date(lastSync))
                Label("$sync · toutes les 30 min", Soft, 16.sp)
            }
        }
        item {
            Card {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    Ring(energy, "ÉNERGIE", 140.dp)
                    Ring(sleepScore, "SOMMEIL", 140.dp)
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                for (m in listOf(PhoneMetric.SLEEP_MIN, PhoneMetric.STEPS, PhoneMetric.DISTANCE_M)) {
                    Box(Modifier.weight(1f)) { Stat(m, reading(values, m)) }
                }
            }
        }
        item {
            Button(
                onClick = onSync, enabled = !busy,
                modifier = Modifier.fillMaxWidth().height(52.dp),
                shape = RoundedCornerShape(26.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = ButtonBg, contentColor = Bg,
                    disabledContainerColor = Track, disabledContentColor = Soft,
                ),
            ) {
                Label(if (busy) "Synchronisation…" else "Synchroniser maintenant", Color.Unspecified, 19.sp, bold = true)
            }
        }
        if (status != null && !busy) {
            item { Label(status, if (error) Alert else Soft, 16.sp) }
        }
        if (others.isNotEmpty()) {
            item { Label("TOUTES LES DONNÉES", Soft, 15.sp, spacing = 1.5.sp, modifier = Modifier.padding(top = 8.dp)) }
            items(others.chunked(2)) { pair ->
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    pair.forEach { r -> Box(Modifier.weight(1f)) { Tile(r) } }
                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun Card(content: @Composable () -> Unit) {
    Box(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp)).background(CardBg).padding(vertical = 20.dp),
    ) { content() }
}

/** Anneau de score sur 100, valeur au centre. */
@Composable
private fun Ring(r: Reading?, label: String, size: Dp) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.size(size), contentAlignment = Alignment.Center) {
            Canvas(Modifier.fillMaxSize()) {
                val w = 13.dp.toPx()
                val arc = Size(this.size.width - w, this.size.height - w)
                val tl = Offset(w / 2, w / 2)
                drawArc(Track, 0f, 360f, false, tl, arc, style = Stroke(w))
                val p = r?.progress ?: 0f
                if (p > 0f) drawArc(Accent, -90f, 360f * p, false, tl, arc, style = Stroke(w, cap = StrokeCap.Round))
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Label(r?.value ?: "--", Ink, 46.sp, bold = true)
                Label("/ 100", Soft, 14.sp)
            }
        }
        Spacer(Modifier.height(8.dp))
        Label(label, Soft, 15.sp, spacing = 1.5.sp)
    }
}

/** Vignette de la ligne du haut : libellé, grande valeur, barre ou complément. */
@Composable
private fun Stat(m: PhoneMetric, r: Reading?) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(CardBg).padding(14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(painterResource(m.icon), null, tint = Accent, modifier = Modifier.size(20.dp))
        Label(m.title, Soft, 13.sp, spacing = 1.sp)
        Label(r?.value ?: "--", Ink, 26.sp, bold = true)
        if (r?.progress != null) Bar(r.progress) else Label(r?.sub ?: " ", Accent, 13.sp)
    }
}

/** Carte de la liste : pictogramme, titre, valeur, objectif et barre. */
@Composable
private fun Tile(r: Reading) {
    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(CardBg).padding(14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(painterResource(r.metric.icon), null, tint = Accent, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(6.dp))
            Label(r.metric.title, Soft, 13.sp, spacing = 1.sp)
        }
        Row(verticalAlignment = Alignment.Bottom) {
            Label(r.value, Ink, 28.sp, bold = true)
            r.sub?.let {
                Spacer(Modifier.width(5.dp))
                Label(it, Accent, 14.sp, modifier = Modifier.padding(bottom = 4.dp))
            }
        }
        r.progress?.let { Bar(it) }
    }
}

@Composable
private fun Bar(p: Float) {
    Box(Modifier.fillMaxWidth().padding(top = 6.dp).height(6.dp).clip(RoundedCornerShape(3.dp)).background(Track)) {
        Box(Modifier.fillMaxWidth(p).height(6.dp).clip(RoundedCornerShape(3.dp)).background(Accent))
    }
}

@Composable
private fun Label(
    text: String, color: Color, size: TextUnit, bold: Boolean = false,
    spacing: TextUnit = TextUnit.Unspecified, modifier: Modifier = Modifier,
) {
    Text(
        text, color = color, fontSize = size, fontFamily = Barlow, letterSpacing = spacing,
        fontWeight = if (bold) FontWeight.SemiBold else FontWeight.Medium, modifier = modifier,
    )
}
