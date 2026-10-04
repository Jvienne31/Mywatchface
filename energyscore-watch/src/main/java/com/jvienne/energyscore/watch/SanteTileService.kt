package com.jvienne.energyscore.watch

import android.content.ComponentName
import android.content.Context
import androidx.wear.protolayout.ActionBuilders
import androidx.wear.protolayout.DeviceParametersBuilders.DeviceParameters
import androidx.wear.protolayout.DimensionBuilders.dp
import androidx.wear.protolayout.DimensionBuilders.expand
import androidx.wear.protolayout.DimensionBuilders.weight
import androidx.wear.protolayout.LayoutElementBuilders
import androidx.wear.protolayout.LayoutElementBuilders.Column
import androidx.wear.protolayout.LayoutElementBuilders.LayoutElement
import androidx.wear.protolayout.LayoutElementBuilders.Spacer
import androidx.wear.protolayout.ModifiersBuilders.Clickable
import androidx.wear.protolayout.ResourceBuilders
import androidx.wear.protolayout.TimelineBuilders
import androidx.wear.protolayout.material3.CardColors
import androidx.wear.protolayout.material3.ColorScheme
import androidx.wear.protolayout.material3.MaterialScope
import androidx.wear.protolayout.material3.PrimaryLayoutMargins
import androidx.wear.protolayout.material3.ProgressIndicatorColors
import androidx.wear.protolayout.material3.Typography
import androidx.wear.protolayout.material3.buttonGroup
import androidx.wear.protolayout.material3.circularProgressIndicator
import androidx.wear.protolayout.material3.graphicDataCard
import androidx.wear.protolayout.material3.materialScope
import androidx.wear.protolayout.material3.primaryLayout
import androidx.wear.protolayout.material3.text
import androidx.wear.protolayout.material3.textDataCard
import androidx.wear.protolayout.material3.textEdgeButton
import androidx.wear.protolayout.modifiers.clickable
import androidx.wear.protolayout.types.LayoutColor
import androidx.wear.protolayout.types.layoutString
import androidx.wear.tiles.RequestBuilders
import androidx.wear.tiles.TileBuilders
import androidx.wear.tiles.TileService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

/**
 * Tuile « Santé du jour », style Material 3 Expressive (modèle « Goal » des Golden Tiles de
 * Google) : grande pastille du score d'énergie avec son anneau, trois pastilles sommeil / pas /
 * distance, bouton de bord « Détails ». Lit le même cache que les complications
 * ([HealthStore]) et se redessine à chaque nouvelle donnée ([refresh]).
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
        val energy = reading(Metric.ENERGY)
        val sleep = reading(Metric.SLEEP_MIN)
        val sleepScore = reading(Metric.SLEEP_SCORE)
        val steps = reading(Metric.STEPS)
        val distance = reading(Metric.DISTANCE_M)
        val open = clickable(
            ActionBuilders.launchAction(ComponentName(packageName, MainActivity::class.java.name)),
            "ouvrir",
        )
        return materialScope(this, device, allowDynamicTheme = false, defaultColorScheme = LAGUNE) {
            primaryLayout(
                titleSlot = { text("Santé du jour".layoutString) },
                margins = PrimaryLayoutMargins.MIN_PRIMARY_LAYOUT_MARGIN,
                mainSlot = {
                    Column.Builder()
                        .setWidth(expand())
                        .setHeight(expand())
                        .addContent(energyCard(energy, open))
                        .addContent(Spacer.Builder().setHeight(dp(4f)).build())
                        .addContent(
                            buttonGroup(height = weight(1f), spacing = 4f) {
                                buttonGroupItem {
                                    mini(open, sleep?.value, "Sommeil", sleepScore?.let { "score ${it.value}" })
                                }
                                buttonGroupItem {
                                    mini(open, steps?.value?.let(::compactSteps), "Pas",
                                        steps?.progress?.let { "${(it * 100).toInt()} %" })
                                }
                                buttonGroupItem {
                                    mini(open, distance?.value?.substringBefore(' '), "Distance",
                                        distance?.value?.substringAfter(' ', ""))
                                }
                            }
                        )
                        .build()
                },
                bottomSlot = { textEdgeButton(onClick = open) { text("Détails".layoutString) } },
            )
        }
    }

    /** Grande pastille : score d'énergie, « sur 100 », anneau de progression à droite. */
    private fun MaterialScope.energyCard(energy: Reading?, open: Clickable): LayoutElement =
        graphicDataCard(
            onClick = open,
            height = weight(1.3f),
            colors = CardColors(
                backgroundColor = LayoutColor(Lagune.CARD),
                titleColor = LayoutColor(Lagune.INK),
                contentColor = LayoutColor(Lagune.ACCENT),
            ),
            horizontalAlignment = LayoutElementBuilders.HORIZONTAL_ALIGN_END,
            title = { text((energy?.value ?: "--").layoutString, typography = Typography.NUMERAL_MEDIUM) },
            content = { text("Énergie / 100".layoutString, typography = Typography.LABEL_SMALL) },
            graphic = {
                circularProgressIndicator(
                    staticProgress = energy?.progress ?: 0f,
                    colors = ProgressIndicatorColors(LayoutColor(Lagune.ACCENT), LayoutColor(Lagune.TRACK)),
                )
            },
        )

    /** Mini-pastille : valeur, libellé, complément. */
    private fun MaterialScope.mini(open: Clickable, value: String?, label: String, sub: String?): LayoutElement {
        val secondary: (MaterialScope.() -> LayoutElement)? =
            if (sub.isNullOrEmpty()) null else { { text(sub.layoutString) } }
        return textDataCard(
            onClick = open,
            width = expand(),
            height = expand(),
            colors = CardColors(
                backgroundColor = LayoutColor(Lagune.CARD_2),
                titleColor = LayoutColor(Lagune.INK),
                contentColor = LayoutColor(Lagune.SOFT),
                secondaryTextColor = LayoutColor(Lagune.ACCENT),
            ),
            title = { text((value ?: "--").layoutString) },
            content = { text(label.layoutString) },
            secondaryText = secondary,
        )
    }

    /** « 7 412 » tient mal dans une mini-pastille : « 7,4k » au-delà de 9 999. */
    private fun compactSteps(v: String): String {
        val n = v.filter(Char::isDigit).toIntOrNull() ?: return v
        return if (n < 10_000) v else String.format(java.util.Locale.FRANCE, "%.1fk", n / 1000f)
    }

    companion object {
        private const val RESOURCES_VERSION = "2"

        /** Couleurs Lagune pour les rôles Material 3 utilisés par les composants. */
        private val LAGUNE = ColorScheme(
            primary = LayoutColor(Lagune.ACCENT),
            onPrimary = LayoutColor(Lagune.BG),
            primaryContainer = LayoutColor(Lagune.BUTTON),
            onPrimaryContainer = LayoutColor(Lagune.INK),
            surfaceContainer = LayoutColor(Lagune.CARD),
            surfaceContainerHigh = LayoutColor(Lagune.CARD_2),
            onSurface = LayoutColor(Lagune.INK),
            onSurfaceVariant = LayoutColor(Lagune.SOFT),
            background = LayoutColor(Lagune.BG),
            onBackground = LayoutColor(Lagune.INK),
        )

        /** Demande au système de redessiner la tuile (nouvelles données reçues ou mesurées). */
        fun refresh(context: Context) {
            TileService.getUpdater(context).requestUpdate(SanteTileService::class.java)
        }
    }
}
