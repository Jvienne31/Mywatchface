package com.jvienne.energyscore.watch

import android.graphics.drawable.Icon
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.GoalProgressComplicationData
import androidx.wear.watchface.complications.data.LongTextComplicationData
import androidx.wear.watchface.complications.data.MonochromaticImage
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.RangedValueComplicationData
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService

/**
 * Fournisseur de complication pour une donnée Samsung Health ([metric]). Il ne lit jamais
 * Samsung Health lui-même : il sert la dernière valeur poussée par l'appli téléphone et mise
 * en cache par [HealthSyncListenerService]. Les sous-classes (Providers.kt) ne font que
 * choisir la donnée : chaque complication doit être un service distinct.
 *
 * Types : SHORT_TEXT et LONG_TEXT toujours ; RANGED_VALUE si la donnée a un objectif ou un
 * maximum (jauge des dômes de Prisme) ; GOAL_PROGRESS si elle a un objectif.
 */
abstract class MetricComplicationService : SuspendingComplicationDataSourceService() {

    abstract val metric: Metric

    override fun getPreviewData(type: ComplicationType): ComplicationData? =
        build(type, metric.preview, metric.previewGoal, if (metric.format == Format.PRESSURE) 79f else null)

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData? {
        val value = HealthStore.get(this, metric.key)
        val goal = metric.goalKey?.let { HealthStore.get(this, it) }
        val extra = if (metric.format == Format.PRESSURE) HealthStore.get(this, "bp_dia") else null
        return build(request.complicationType, value, goal, extra)
    }

    private fun build(type: ComplicationType, value: Float?, goal: Float?, extra: Float?): ComplicationData? {
        val text = PlainComplicationText.Builder(value?.let { metric.format.text(it, extra) } ?: "--").build()
        val title = PlainComplicationText.Builder(metric.title).build()
        val description = PlainComplicationText.Builder(metric.label).build()
        val icon = MonochromaticImage.Builder(Icon.createWithResource(this, metric.icon)).build()

        return when (type) {
            ComplicationType.SHORT_TEXT -> ShortTextComplicationData.Builder(text, description)
                .setTitle(title).setMonochromaticImage(icon).build()

            ComplicationType.LONG_TEXT -> LongTextComplicationData.Builder(text, description)
                .setTitle(title).setMonochromaticImage(icon).build()

            ComplicationType.RANGED_VALUE -> {
                // objectif, sinon maximum fixe, sinon la valeur elle-même (jauge pleine)
                val max = (goal ?: metric.max ?: value ?: 1f).coerceAtLeast(1f)
                RangedValueComplicationData.Builder(
                    value = (value ?: 0f).coerceIn(0f, max), min = 0f, max = max,
                    contentDescription = description,
                ).setText(text).setTitle(title).setMonochromaticImage(icon).build()
            }

            ComplicationType.GOAL_PROGRESS -> {
                val target = (goal ?: metric.previewGoal ?: 1f).coerceAtLeast(1f)
                GoalProgressComplicationData.Builder(value ?: 0f, target, description)
                    .setText(text).setTitle(title).setMonochromaticImage(icon).build()
            }

            else -> null
        }
    }
}
