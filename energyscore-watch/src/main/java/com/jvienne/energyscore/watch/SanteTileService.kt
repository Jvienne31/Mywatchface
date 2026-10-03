package com.jvienne.energyscore.watch

import android.content.Context
import android.text.format.DateFormat
import androidx.wear.protolayout.ActionBuilders
import androidx.wear.protolayout.ColorBuilders.argb
import androidx.wear.protolayout.DeviceParametersBuilders.DeviceParameters
import androidx.wear.protolayout.DimensionBuilders.degrees
import androidx.wear.protolayout.DimensionBuilders.dp
import androidx.wear.protolayout.DimensionBuilders.expand
import androidx.wear.protolayout.DimensionBuilders.sp
import androidx.wear.protolayout.LayoutElementBuilders
import androidx.wear.protolayout.LayoutElementBuilders.Arc
import androidx.wear.protolayout.LayoutElementBuilders.ArcLine
import androidx.wear.protolayout.LayoutElementBuilders.Box
import androidx.wear.protolayout.LayoutElementBuilders.Column
import androidx.wear.protolayout.LayoutElementBuilders.FontStyle
import androidx.wear.protolayout.LayoutElementBuilders.LayoutElement
import androidx.wear.protolayout.LayoutElementBuilders.Row
import androidx.wear.protolayout.LayoutElementBuilders.Spacer
import androidx.wear.protolayout.LayoutElementBuilders.Text
import androidx.wear.protolayout.ModifiersBuilders
import androidx.wear.protolayout.ResourceBuilders
import androidx.wear.protolayout.TimelineBuilders
import androidx.wear.tiles.RequestBuilders
import androidx.wear.tiles.TileBuilders
import androidx.wear.tiles.TileService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

/**
 * Tuile « Santé du jour » : depuis le cadran, on glisse vers la gauche et on voit en grand le
 * score d'énergie (anneau), le sommeil, les pas et la distance. Elle lit le même cache que les
 * complications ([HealthStore]) et se redessine à chaque nouvelle donnée ([refresh]).
 * Toucher la tuile ouvre l'écran de l'appli (toutes les données).
 */
class SanteTileService : TileService() {

    override fun onTileRequest(requestParams: RequestBuilders.TileRequest): ListenableFuture<TileBuilders.Tile> {
        val tile = TileBuilders.Tile.Builder()
            .setResourcesVersion(RESOURCES_VERSION)
            .setFreshnessIntervalMillis(30 * 60 * 1000L)
            .setTileTimeline(TimelineBuilders.Timeline.fromLayoutElement(layout(requestParams.deviceConfiguration)))
            .build()
        return Futures.immediateFuture(tile)
    }

    override fun onTileResourcesRequest(
        requestParams: RequestBuilders.ResourcesRequest,
    ): ListenableFuture<ResourceBuilders.Resources> =
        Futures.immediateFuture(ResourceBuilders.Resources.Builder().setVersion(RESOURCES_VERSION).build())

    private fun layout(device: DeviceParameters): LayoutElement {
        // Tailles prévues pour un écran d'environ 225 dp (Watch8 Classic 46 mm), réduites sur
        // les petits écrans.
        val k = (device.screenWidthDp / 225f).coerceIn(0.8f, 1.2f)
        val energy = reading(Metric.ENERGY)
        val sleep = reading(Metric.SLEEP_MIN)
        val sleepScore = reading(Metric.SLEEP_SCORE)
        val steps = reading(Metric.STEPS)
        val distance = reading(Metric.DISTANCE_M)
        val kcal = reading(Metric.ACTIVE_KCAL)

        val ts = HealthStore.lastUpdate(this)
        val header = if (ts == 0L) "SANTÉ SYNC" else "MAJ " + DateFormat.getTimeFormat(this).format(ts)

        val open = ModifiersBuilders.Clickable.Builder()
            .setId("ouvrir")
            .setOnClick(
                ActionBuilders.LaunchAction.Builder()
                    .setAndroidActivity(
                        ActionBuilders.AndroidActivity.Builder()
                            .setPackageName(packageName)
                            .setClassName(MainActivity::class.java.name)
                            .build()
                    ).build()
            ).build()

        val content = Column.Builder()
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)
            .addContent(text(header, 11f * k, Lagune.ACCENT, medium = true))
            .addContent(space(4f * k))
            .addContent(energyRing(energy, 82f * k, k))
            .addContent(space(8f * k))
            .addContent(
                Row.Builder()
                    .setVerticalAlignment(LayoutElementBuilders.VERTICAL_ALIGN_TOP)
                    .addContent(stat("SOMMEIL", sleep?.value, sleepScore?.let { "score ${it.value}" }, null, k))
                    .addContent(stat("PAS", steps?.value, null, steps?.progress, k))
                    .addContent(stat("DISTANCE", distance?.value, kcal?.let { "${it.value} kcal" }, null, k))
                    .build()
            )
            .addContent(space(8f * k))
            .addContent(button("Détails", k))
            .build()

        return Box.Builder()
            .setWidth(expand())
            .setHeight(expand())
            .setModifiers(
                ModifiersBuilders.Modifiers.Builder()
                    .setClickable(open)
                    .setBackground(ModifiersBuilders.Background.Builder().setColor(argb(Lagune.BG)).build())
                    .build()
            )
            .addContent(content)
            .build()
    }

    /** Anneau du score d'énergie (sur 100) avec la valeur au centre. */
    private fun energyRing(energy: Reading?, size: Float, k: Float): LayoutElement {
        val progress = energy?.progress ?: 0f
        fun arc(sweep: Float, color: Int) = Arc.Builder()
            .setAnchorAngle(degrees(0f))
            .setAnchorType(LayoutElementBuilders.ARC_ANCHOR_START)
            .addContent(
                ArcLine.Builder()
                    .setLength(degrees(sweep))
                    .setThickness(dp(7f * k))
                    .setColor(argb(color))
                    .build()
            ).build()

        val box = Box.Builder()
            .setWidth(dp(size))
            .setHeight(dp(size))
            .addContent(arc(360f, Lagune.TRACK))
        if (progress > 0f) box.addContent(arc(360f * progress, Lagune.ACCENT))
        return box.addContent(
            Column.Builder()
                .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)
                .addContent(text(energy?.value ?: "--", 32f * k, Lagune.INK, bold = true))
                .addContent(text("ÉNERGIE", 10f * k, Lagune.SOFT, medium = true))
                .build()
        ).build()
    }

    /** Une colonne : libellé, grande valeur, puis complément ou barre de progression. */
    private fun stat(label: String, value: String?, sub: String?, progress: Float?, k: Float): LayoutElement {
        val width = 64f * k
        val col = Column.Builder()
            .setWidth(dp(width))
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)
            .addContent(text(label, 10f * k, Lagune.SOFT, medium = true))
            .addContent(text(value ?: "--", 19f * k, Lagune.INK, bold = true))
        when {
            progress != null -> col.addContent(space(3f * k)).addContent(bar(progress, 44f * k, 4f * k))
            sub != null -> col.addContent(text(sub, 10f * k, Lagune.ACCENT, medium = true))
        }
        return col.build()
    }

    private fun bar(progress: Float, width: Float, height: Float): LayoutElement {
        fun piece(w: Float, color: Int) = Box.Builder()
            .setWidth(dp(w))
            .setHeight(dp(height))
            .setModifiers(
                ModifiersBuilders.Modifiers.Builder().setBackground(
                    ModifiersBuilders.Background.Builder()
                        .setColor(argb(color))
                        .setCorner(ModifiersBuilders.Corner.Builder().setRadius(dp(height / 2)).build())
                        .build()
                ).build()
            ).build()
        val track = Box.Builder()
            .setWidth(dp(width))
            .setHeight(dp(height))
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_START)
            .addContent(piece(width, Lagune.TRACK))
        if (progress > 0f) track.addContent(piece((width * progress).coerceAtLeast(height), Lagune.ACCENT))
        return track.build()
    }

    private fun button(label: String, k: Float): LayoutElement = Box.Builder()
        .setWidth(dp(84f * k))
        .setHeight(dp(26f * k))
        .setModifiers(
            ModifiersBuilders.Modifiers.Builder().setBackground(
                ModifiersBuilders.Background.Builder()
                    .setColor(argb(Lagune.BUTTON))
                    .setCorner(ModifiersBuilders.Corner.Builder().setRadius(dp(13f * k)).build())
                    .build()
            ).build()
        )
        .addContent(text(label, 13f * k, Lagune.BG, bold = true))
        .build()

    private fun space(h: Float): LayoutElement = Spacer.Builder().setHeight(dp(h)).build()

    private fun text(s: String, size: Float, color: Int, bold: Boolean = false, medium: Boolean = false): LayoutElement =
        Text.Builder()
            .setText(s)
            .setMaxLines(1)
            .setFontStyle(
                FontStyle.Builder()
                    .setSize(sp(size))
                    .setColor(argb(color))
                    .setWeight(
                        when {
                            bold -> LayoutElementBuilders.FONT_WEIGHT_BOLD
                            medium -> LayoutElementBuilders.FONT_WEIGHT_MEDIUM
                            else -> LayoutElementBuilders.FONT_WEIGHT_NORMAL
                        }
                    ).build()
            ).build()

    companion object {
        private const val RESOURCES_VERSION = "1"

        /** Demande au système de redessiner la tuile (nouvelles données reçues ou mesurées). */
        fun refresh(context: Context) {
            TileService.getUpdater(context).requestUpdate(SanteTileService::class.java)
        }
    }
}
