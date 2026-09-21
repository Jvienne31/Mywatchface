package com.jvienne.energyscore.watch

import android.graphics.drawable.Icon
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationText
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.MonochromaticImage
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.RangedValueComplicationData
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService

/**
 * Fournisseur de complication tiers pour le score d'énergie Samsung Health.
 *
 * Ce service ne parle jamais à Samsung Health directement : il sert simplement la dernière
 * valeur poussée par le module téléphone (`energyscore-phone`) via le Data Layer Wear OS et mise
 * en cache par [EnergyScoreSyncListenerService]. Une fois cette appli installée sur la montre, le
 * cadran Mywatchface peut sélectionner "Score d'énergie" dans le choix des complications de
 * n'importe lequel de ses 8 emplacements (SHORT_TEXT / RANGED_VALUE), exactement comme un
 * fournisseur Samsung natif.
 */
class EnergyScoreComplicationService : SuspendingComplicationDataSourceService() {

    override fun getPreviewData(type: ComplicationType): ComplicationData? {
        return buildData(previewScore = 82, type = type)
    }

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData? {
        val score = EnergyScoreStore.read(applicationContext)
        return buildData(previewScore = score, type = request.complicationType)
    }

    private fun buildData(previewScore: Int?, type: ComplicationType): ComplicationData? {
        val icon = MonochromaticImage.Builder(
            Icon.createWithResource(this, R.drawable.ic_energy_score)
        ).build()

        return when (type) {
            ComplicationType.SHORT_TEXT -> {
                val text: ComplicationText = if (previewScore != null) {
                    PlainComplicationText.Builder(previewScore.toString()).build()
                } else {
                    PlainComplicationText.Builder("--").build()
                }
                ShortTextComplicationData.Builder(
                    text = text,
                    contentDescription = PlainComplicationText.Builder("Score d'énergie").build()
                ).setMonochromaticImage(icon).build()
            }

            ComplicationType.RANGED_VALUE -> {
                val value = (previewScore ?: 0).toFloat()
                RangedValueComplicationData.Builder(
                    value = value,
                    min = 0f,
                    max = 100f,
                    contentDescription = PlainComplicationText.Builder("Score d'énergie").build()
                )
                    .setText(PlainComplicationText.Builder(value.toInt().toString()).build())
                    .setMonochromaticImage(icon)
                    .build()
            }

            else -> null
        }
    }
}
