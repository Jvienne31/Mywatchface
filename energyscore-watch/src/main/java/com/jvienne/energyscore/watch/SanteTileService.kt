package com.jvienne.energyscore.watch

import android.content.ComponentName
import android.content.Context
import androidx.wear.protolayout.ActionBuilders
import androidx.wear.protolayout.DeviceParametersBuilders.DeviceParameters
import androidx.wear.protolayout.DimensionBuilders.dp
import androidx.wear.protolayout.DimensionBuilders.expand
import androidx.wear.protolayout.DimensionBuilders.weight
import androidx.wear.protolayout.LayoutElementBuilders
import androidx.wear.protolayout.LayoutElementBuilders.Box
import androidx.wear.protolayout.LayoutElementBuilders.Column
import androidx.wear.protolayout.LayoutElementBuilders.LayoutElement
import androidx.wear.protolayout.LayoutElementBuilders.Spacer
import androidx.wear.protolayout.ModifiersBuilders.Clickable
import androidx.wear.protolayout.ResourceBuilders
import androidx.wear.protolayout.TimelineBuilders
import androidx.wear.protolayout.LayoutElementBuilders.Row
import androidx.wear.protolayout.material3.ColorScheme
import androidx.wear.protolayout.material3.MaterialScope
import androidx.wear.protolayout.material3.PrimaryLayoutMargins
import androidx.wear.protolayout.material3.ProgressIndicatorColors
import androidx.wear.protolayout.material3.Typography
import androidx.wear.protolayout.material3.buttonGroup
import androidx.wear.protolayout.material3.circularProgressIndicator
import androidx.wear.protolayout.material3.icon
import androidx.wear.protolayout.material3.card
import androidx.wear.protolayout.material3.materialScope
import androidx.wear.protolayout.material3.primaryLayout
import androidx.wear.protolayout.material3.text
import androidx.wear.protolayout.material3.textEdgeButton
import androidx.wear.protolayout.modifiers.LayoutModifier
import androidx.wear.protolayout.modifiers.background
import androidx.wear.protolayout.modifiers.clickable
import androidx.wear.protolayout.types.LayoutColor
import androidx.wear.protolayout.types.layoutString
import androidx.wear.tiles.RequestBuilders
import androidx.wear.tiles.TileBuilders
import androidx.wear.tiles.TileService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

/**
 * Tuile « Santé du jour », style Material 3 Expressive (d'après les Golden Tiles de Google) :
 * grande pastille du score d'énergie avec son anneau, trois pastilles sommeil / pas /
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
        Futures.immediateFuture(
            ResourceBuilders.Resources.Builder()
                .setVersion(RESOURCES_VERSION)
                .apply {
                    ICONS.forEach { (id, res) ->
                        addIdToImageMapping(
                            id,
                            ResourceBuilders.ImageResource.Builder()
                                .setAndroidResourceByResId(
                                    ResourceBuilders.AndroidImageResourceByResId.Builder().setResourceId(res).build()
                                ).build(),
                        )
                    }
                }
                .build()
        )

    private fun layout(device: DeviceParameters): LayoutElement {
        val energy = reading(Metric.ENERGY)
        val sleep = reading(Metric.SLEEP_MIN)
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
                        .addContent(Spacer.Builder().setHeight(dp(6f)).build())
                        .addContent(
                            buttonGroup(height = weight(1f), spacing = 4f) {
                                buttonGroupItem { mini(open, sleep?.value, "moon") }
                                buttonGroupItem { mini(open, steps?.value?.let(::compactSteps), "steps") }
                                buttonGroupItem { mini(open, distance?.value, "pin") }
                            }
                        )
                        .build()
                },
                bottomSlot = { textEdgeButton(onClick = open) { text("Détails".layoutString) } },
            )
        }
    }

    /**
     * Grande pastille sur une seule ligne : éclair, score, « /100 », anneau à droite.
     * Contenu dessiné à la main (card) : les cartes « de données » de Material 3 masquent leurs
     * textes quand la hauteur manque [montre]. Textes non agrandis par la taille de police du
     * système (scalable = false), sinon ils sont coupés.
     */
    private fun MaterialScope.energyCard(energy: Reading?, open: Clickable): LayoutElement =
        card(
            onClick = open,
            modifier = LayoutModifier.background(LayoutColor(Lagune.CARD)),
            width = expand(),
            height = weight(1f),
        ) {
            Row.Builder()
                .setWidth(expand())
                .setVerticalAlignment(LayoutElementBuilders.VERTICAL_ALIGN_CENTER)
                .addContent(icon("bolt", width = dp(20f), height = dp(20f), tintColor = LayoutColor(Lagune.ACCENT)))
                .addContent(Spacer.Builder().setWidth(dp(6f)).build())
                .addContent(text((energy?.value ?: "--").layoutString, typography = Typography.NUMERAL_SMALL,
                    color = LayoutColor(Lagune.INK), scalable = false))
                .addContent(Spacer.Builder().setWidth(dp(3f)).build())
                .addContent(text("/100".layoutString, typography = Typography.LABEL_MEDIUM,
                    color = LayoutColor(Lagune.SOFT), scalable = false))
                .addContent(Box.Builder().setWidth(weight(1f)).build())
                .addContent(
                    circularProgressIndicator(
                        staticProgress = energy?.progress ?: 0f,
                        size = dp(36f),
                        strokeWidth = 6f,
                        colors = ProgressIndicatorColors(LayoutColor(Lagune.ACCENT), LayoutColor(Lagune.TRACK)),
                    )
                )
                .build()
        }

    /** Mini-pastille : pictogramme (sommeil, pas, distance) au-dessus de la valeur. */
    private fun MaterialScope.mini(open: Clickable, value: String?, iconId: String): LayoutElement =
        card(
            onClick = open,
            modifier = LayoutModifier.background(LayoutColor(Lagune.CARD_2)),
            width = expand(),
            height = expand(),
        ) {
            Column.Builder()
                .setWidth(expand())
                .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)
                .addContent(icon(iconId, width = dp(18f), height = dp(18f), tintColor = LayoutColor(Lagune.ACCENT)))
                .addContent(Spacer.Builder().setHeight(dp(2f)).build())
                .addContent(text((value ?: "--").layoutString, typography = Typography.TITLE_MEDIUM,
                    color = LayoutColor(Lagune.INK), maxLines = 1, scalable = false))
                .build()
        }

    /** « 7 412 » tient mal dans une mini-pastille : « 7,4k » au-delà de 9 999. */
    private fun compactSteps(v: String): String {
        val n = v.filter(Char::isDigit).toIntOrNull() ?: return v
        return if (n < 10_000) v else String.format(java.util.Locale.FRANCE, "%.1fk", n / 1000f)
    }

    companion object {
        private const val RESOURCES_VERSION = "3"

        /** Pictogrammes de la tuile (mêmes dessins que les complications). */
        private val ICONS = mapOf(
            "bolt" to R.drawable.ic_m_bolt,
            "moon" to R.drawable.ic_m_moon,
            "steps" to R.drawable.ic_m_steps,
            "pin" to R.drawable.ic_m_pin,
        )

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
