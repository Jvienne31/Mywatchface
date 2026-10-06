// FICHIER GÉNÉRÉ par energyscore-watch/tools/gen_metrics.py : ne pas éditer à la main.

package com.jvienne.energyscore.watch

class EnergyProvider : MetricComplicationService() { override val metric = Metric.ENERGY }
class SleepScoreProvider : MetricComplicationService() { override val metric = Metric.SLEEP_SCORE }
class SleepMinProvider : MetricComplicationService() { override val metric = Metric.SLEEP_MIN }
class StepsProvider : MetricComplicationService() { override val metric = Metric.STEPS }
class DistanceMProvider : MetricComplicationService() { override val metric = Metric.DISTANCE_M }
class ActiveKcalProvider : MetricComplicationService() { override val metric = Metric.ACTIVE_KCAL }
class TotalKcalProvider : MetricComplicationService() { override val metric = Metric.TOTAL_KCAL }
class ActiveMinProvider : MetricComplicationService() { override val metric = Metric.ACTIVE_MIN }
class FloorsProvider : MetricComplicationService() { override val metric = Metric.FLOORS }
class WaterMlProvider : MetricComplicationService() { override val metric = Metric.WATER_ML }
class FoodKcalProvider : MetricComplicationService() { override val metric = Metric.FOOD_KCAL }
class HrLastProvider : MetricComplicationService() { override val metric = Metric.HR_LAST }
class HrMinProvider : MetricComplicationService() { override val metric = Metric.HR_MIN }
class HrMaxProvider : MetricComplicationService() { override val metric = Metric.HR_MAX }
class Spo2Provider : MetricComplicationService() { override val metric = Metric.SPO2 }
class SkinTempProvider : MetricComplicationService() { override val metric = Metric.SKIN_TEMP }
class BodyTempProvider : MetricComplicationService() { override val metric = Metric.BODY_TEMP }
class BpSysProvider : MetricComplicationService() { override val metric = Metric.BP_SYS }
class GlucoseProvider : MetricComplicationService() { override val metric = Metric.GLUCOSE }
class WeightProvider : MetricComplicationService() { override val metric = Metric.WEIGHT }
class BodyFatProvider : MetricComplicationService() { override val metric = Metric.BODY_FAT }
class MuscleProvider : MetricComplicationService() { override val metric = Metric.MUSCLE }
class BmiProvider : MetricComplicationService() { override val metric = Metric.BMI }
class Vo2maxProvider : MetricComplicationService() { override val metric = Metric.VO2MAX }
class LastExMinProvider : MetricComplicationService() { override val metric = Metric.LAST_EX_MIN }
class LastExMProvider : MetricComplicationService() { override val metric = Metric.LAST_EX_M }

/** Tous les fournisseurs, pour demander leur mise à jour à la réception de données. */
val ALL_PROVIDERS = listOf(
    EnergyProvider::class.java,
    SleepScoreProvider::class.java,
    SleepMinProvider::class.java,
    StepsProvider::class.java,
    DistanceMProvider::class.java,
    ActiveKcalProvider::class.java,
    TotalKcalProvider::class.java,
    ActiveMinProvider::class.java,
    FloorsProvider::class.java,
    WaterMlProvider::class.java,
    FoodKcalProvider::class.java,
    HrLastProvider::class.java,
    HrMinProvider::class.java,
    HrMaxProvider::class.java,
    Spo2Provider::class.java,
    SkinTempProvider::class.java,
    BodyTempProvider::class.java,
    BpSysProvider::class.java,
    GlucoseProvider::class.java,
    WeightProvider::class.java,
    BodyFatProvider::class.java,
    MuscleProvider::class.java,
    BmiProvider::class.java,
    Vo2maxProvider::class.java,
    LastExMinProvider::class.java,
    LastExMProvider::class.java,
)
