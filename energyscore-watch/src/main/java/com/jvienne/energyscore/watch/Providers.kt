// FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py : ne pas éditer à la main.

package com.jvienne.energyscore.watch

class EnergyProvider : MetricComplicationService() { override val metric = Metric.ENERGY }
class SleepScoreProvider : MetricComplicationService() { override val metric = Metric.SLEEP_SCORE }

/** Tous les fournisseurs, pour demander leur mise à jour à la réception de données. */
val ALL_PROVIDERS = listOf(
    EnergyProvider::class.java,
    SleepScoreProvider::class.java,
)
