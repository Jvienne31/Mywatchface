package com.jvienne.energyscore.watch

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.text.format.DateFormat
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.focusable
import androidx.compose.foundation.gestures.scrollBy
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.rotary.onRotaryScrollEvent
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.foundation.lazy.AutoCenteringParams
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.items
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.Icon
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.PositionIndicator
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.compose.material.Vignette
import androidx.wear.compose.material.VignettePosition
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

private val Bg = Color(Lagune.BG)
private val CardBg = Color(Lagune.CARD)
private val Track = Color(Lagune.TRACK)
private val Ink = Color(Lagune.INK)
private val Accent = Color(Lagune.ACCENT)
private val Soft = Color(Lagune.SOFT)
private val Barlow = FontFamily(
    Font(R.font.barlowcondensed_medium, FontWeight.Medium),
    Font(R.font.barlowcondensed_semibold, FontWeight.SemiBold),
)

/**
 * Écran de l'appli montre (Compose for Wear OS) : toutes les données reçues, en cartes, dans une
 * liste ronde qui défile au doigt ou à la lunette. Toucher une carte ouvre Samsung Health.
 * Demande aussi l'autorisation « activité physique » pour les mesures en direct.
 */
class MainActivity : ComponentActivity() {

    /** Incrémenté à chaque retour sur l'écran : relit le cache. */
    private var version by mutableIntStateOf(0)

    // Cadran Prisme installé par Watch Face Push (Wear OS 6)
    private var prisme by mutableStateOf<PrismeInstaller.State?>(null)
    private var prismeMessage by mutableStateOf<String?>(null)
    private var prismeBusy by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!hasActivityPermission()) askPermission() else PassiveDataService.register(this)
        setContent {
            val tick = version   // relecture du cache quand version change
            val readings = remember(tick) { Metric.values().mapNotNull { reading(it) } }
            val phone = remember(tick) {
                val ts = HealthStore.lastUpdate(this)
                if (ts == 0L) "Téléphone : rien reçu. Ouvrez Santé Sync sur le téléphone."
                else "Téléphone : reçu à ${DateFormat.getTimeFormat(this).format(ts)}"
            }
            val live = remember(tick) { hasActivityPermission() }
            val oldPrisme = remember(tick) { PrismeInstaller.oldInstalled(this) }
            val panel = prisme?.let { PrismePanel(it, prismeMessage, prismeBusy, oldPrisme) }
            SanteScreen(readings, phone, live, ::askPermission, ::openSamsungHealth, panel, ::prismeAction) {
                PrismeInstaller.uninstallOld(this)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        version++
        refreshPrisme()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_ACTIVATE) {
            runPrisme { PrismeInstaller.activate(this) }
            return
        }
        PassiveDataService.register(this)
        version++
    }

    private fun refreshPrisme() {
        if (!PrismeInstaller.supported(this)) return
        lifecycleScope.launch {
            prisme = runCatching { PrismeInstaller.state(this@MainActivity) }
                .onFailure { prismeMessage = "Watch Face Push indisponible : ${it.message}" }
                .getOrNull()
        }
    }

    /** Bouton Prisme : installer, mettre à jour, ou mettre comme cadran actif. */
    private fun prismeAction() {
        val state = prisme ?: return
        if (state.needsInstall || state.needsUpdate) {
            runPrisme {
                val message = PrismeInstaller.installOrUpdate(this)
                if (state.needsInstall) activateOrAsk() ?: message else message
            }
        } else {
            runPrisme { activateOrAsk() ?: "" }
        }
    }

    /** Active Prisme si l'autorisation est accordée ; sinon la demande (null : réponse attendue). */
    private suspend fun activateOrAsk(): String? =
        if (checkSelfPermission(PrismeInstaller.PERMISSION_ACTIVATE) == PackageManager.PERMISSION_GRANTED) {
            PrismeInstaller.activate(this)
        } else {
            requestPermissions(arrayOf(PrismeInstaller.PERMISSION_ACTIVATE), REQUEST_ACTIVATE)
            null
        }

    private fun runPrisme(block: suspend () -> String) {
        if (prismeBusy) return
        lifecycleScope.launch {
            prismeBusy = true
            prismeMessage = runCatching { block() }.getOrElse { "Erreur : ${it.message}" }.ifEmpty { null }
            prisme = runCatching { PrismeInstaller.state(this@MainActivity) }.getOrNull()
            prismeBusy = false
        }
    }

    private fun hasActivityPermission() =
        checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION) == PackageManager.PERMISSION_GRANTED

    private fun askPermission() = requestPermissions(arrayOf(Manifest.permission.ACTIVITY_RECOGNITION), 1)

    private companion object {
        const val REQUEST_ACTIVATE = 2
    }

    private fun openSamsungHealth() {
        packageManager.getLaunchIntentForPackage(MetricComplicationService.SAMSUNG_HEALTH)
            ?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ?.let(::startActivity)
    }
}

@Composable
private fun SanteScreen(
    readings: List<Reading>,
    phoneStatus: String,
    liveGranted: Boolean,
    onAskPermission: () -> Unit,
    onOpen: () -> Unit,
    prisme: PrismePanel?,
    onPrisme: () -> Unit,
    onRemoveOld: () -> Unit,
) {
    val listState = rememberScalingLazyListState()
    val context = LocalContext.current
    var showSources by remember { mutableStateOf(false) }
    val sources = remember(showSources) { if (showSources) ComplicationSources.list(context) else emptyList() }
    val focus = remember { FocusRequester() }
    val scope = rememberCoroutineScope()
    MaterialTheme {
        Scaffold(
            modifier = Modifier.background(Bg),
            timeText = { TimeText() },
            vignette = { Vignette(vignettePosition = VignettePosition.TopAndBottom) },
            positionIndicator = { PositionIndicator(scalingLazyListState = listState) },
        ) {
            ScalingLazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Bg)
                    .onRotaryScrollEvent {
                        scope.launch { listState.scrollBy(it.verticalScrollPixels) }
                        true
                    }
                    .focusRequester(focus)
                    .focusable(),
                state = listState,
                autoCentering = AutoCenteringParams(itemIndex = 1),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                item {
                    Text(
                        "Santé Sync", color = Accent, fontFamily = Barlow, fontWeight = FontWeight.SemiBold,
                        fontSize = 20.sp, modifier = Modifier.padding(top = 18.dp, bottom = 2.dp),
                    )
                }
                if (prisme != null) {
                    item { PrismeSection(prisme, onPrisme, onRemoveOld) }
                }
                if (readings.isEmpty()) {
                    item { Note("Aucune donnée pour l'instant.") }
                }
                items(readings) { r -> MetricCard(r, onOpen) }
                item { Note(phoneStatus) }
                // Relevé des sources de complications (noms exacts pour les préréglages de Prisme)
                item {
                    Chip(
                        onClick = { showSources = !showSources },
                        label = {
                            Text(if (showSources) "Masquer les sources" else "Sources de complications", fontFamily = Barlow)
                        },
                        colors = ChipDefaults.secondaryChipColors(),
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                if (showSources) {
                    items(sources) { src ->
                        Column(Modifier.fillMaxWidth().padding(horizontal = 6.dp)) {
                            Text(src.label, color = Ink, fontFamily = Barlow, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                            Text(src.component, color = Soft, fontSize = 10.sp)
                            Text(src.types, color = Accent, fontSize = 9.sp)
                        }
                    }
                }
                item {
                    if (liveGranted) {
                        Note("Montre : pas, distance, calories et étages en direct")
                    } else {
                        Chip(
                            onClick = onAskPermission,
                            label = { Text("Autoriser les mesures en direct", fontFamily = Barlow) },
                            colors = ChipDefaults.primaryChipColors(backgroundColor = Track, contentColor = Ink),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
        }
    }
    LaunchedEffect(Unit) { focus.requestFocus() }
}

@Composable
private fun MetricCard(r: Reading, onOpen: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(22.dp))
            .background(CardBg)
            .clickable(onClick = onOpen)
            .padding(horizontal = 16.dp, vertical = 8.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                painter = painterResource(r.metric.icon), contentDescription = null,
                tint = Accent, modifier = Modifier.size(14.dp),
            )
            Spacer(Modifier.width(6.dp))
            Text(
                r.metric.title, color = Soft, fontFamily = Barlow, fontWeight = FontWeight.Medium,
                fontSize = 13.sp, letterSpacing = 0.5.sp,
            )
        }
        Row(verticalAlignment = Alignment.Bottom) {
            Text(r.value, color = Ink, fontFamily = Barlow, fontWeight = FontWeight.SemiBold, fontSize = 28.sp)
            r.sub?.let {
                Spacer(Modifier.width(5.dp))
                Text(
                    it, color = Accent, fontFamily = Barlow, fontWeight = FontWeight.Medium, fontSize = 14.sp,
                    modifier = Modifier.padding(bottom = 4.dp),
                )
            }
        }
        r.progress?.let { p ->
            Box(
                Modifier.fillMaxWidth().padding(top = 3.dp).height(5.dp)
                    .clip(RoundedCornerShape(3.dp)).background(Track),
            ) {
                Box(Modifier.fillMaxWidth(p).height(5.dp).clip(RoundedCornerShape(3.dp)).background(Accent))
            }
        }
    }
}

@Composable
private fun Note(text: String) {
    Text(
        text, color = Soft, fontFamily = Barlow, fontWeight = FontWeight.Medium, fontSize = 14.sp,
        textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp),
    )
}

/** Ce que l'écran montre du cadran Prisme (Watch Face Push). */
private data class PrismePanel(
    val state: PrismeInstaller.State,
    val message: String?,
    val busy: Boolean,
    val oldInstalled: Boolean,
)

@Composable
private fun PrismeSection(p: PrismePanel, onClick: () -> Unit, onRemoveOld: () -> Unit) {
    val s = p.state
    val label = when {
        p.busy -> "Installation…"
        s.needsInstall -> "Installer le cadran Prisme"
        s.needsUpdate -> "Mettre à jour Prisme"
        !s.active -> "Mettre Prisme comme cadran"
        else -> null
    }
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        if (label != null) {
            Chip(
                onClick = onClick,
                enabled = !p.busy,
                label = { Text(label, fontFamily = Barlow, fontWeight = FontWeight.SemiBold) },
                colors = ChipDefaults.primaryChipColors(backgroundColor = Accent, contentColor = Bg),
                modifier = Modifier.fillMaxWidth(),
            )
        } else {
            Note("Prisme à jour (version ${s.installedVersion})")
        }
        p.message?.let { Note(it) }
        if (p.oldInstalled) {
            Chip(
                onClick = onRemoveOld,
                label = { Text("Supprimer l'ancien Prisme", fontFamily = Barlow) },
                secondaryLabel = { Text("celui installé à la main", fontFamily = Barlow) },
                colors = ChipDefaults.secondaryChipColors(),
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
            )
        }
    }
}
