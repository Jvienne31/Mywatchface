package com.jvienne.energyscore.phone

import android.app.Activity
import android.content.Context
import android.util.Log
import com.samsung.android.sdk.health.data.HealthDataService
import com.samsung.android.sdk.health.data.data.HealthDataPoint
import com.samsung.android.sdk.health.data.permission.AccessType
import com.samsung.android.sdk.health.data.permission.Permission
import com.samsung.android.sdk.health.data.request.AggregateRequest
import com.samsung.android.sdk.health.data.request.DataType
import com.samsung.android.sdk.health.data.request.DataTypes
import com.samsung.android.sdk.health.data.request.LocalDateFilter
import com.samsung.android.sdk.health.data.request.LocalTimeFilter
import com.samsung.android.sdk.health.data.request.Ordering
import com.samsung.android.sdk.health.data.request.ReadDataRequest
import java.time.Duration
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

/**
 * Lit tout ce que le Samsung Health Data SDK expose en lecture et le ramène à des nombres
 * (clés : [Keys]). Mode développeur Samsung Health : lecture de ses propres données, sans
 * accord partenaire.
 *
 * Écrit d'après les signatures du SDK 1.0.0 (javap sur le .aar) : DataTypes.X pour les
 * instances (builders de lecture), DataType.XType.CHAMP pour les champs et opérations.
 * Chaque donnée est lue séparément : une permission refusée ou une donnée absente n'empêche
 * pas les autres.
 */
class HealthReader(context: Context) {

    private val store = HealthDataService.getStore(context)

    companion object {
        private const val TAG = "HealthReader"

        /** Types lus (permission de lecture demandée pour chacun). */
        val READ_TYPES: List<DataType> = listOf(
            DataTypes.ENERGY_SCORE, DataTypes.SLEEP, DataTypes.SLEEP_GOAL, DataTypes.STEPS,
            DataTypes.STEPS_GOAL, DataTypes.ACTIVITY_SUMMARY, DataTypes.ACTIVE_CALORIES_BURNED_GOAL,
            DataTypes.ACTIVE_TIME_GOAL, DataTypes.FLOORS_CLIMBED, DataTypes.WATER_INTAKE,
            DataTypes.WATER_INTAKE_GOAL, DataTypes.NUTRITION, DataTypes.NUTRITION_GOAL,
            DataTypes.HEART_RATE, DataTypes.BLOOD_OXYGEN, DataTypes.SKIN_TEMPERATURE,
            DataTypes.BODY_TEMPERATURE, DataTypes.BLOOD_PRESSURE, DataTypes.BLOOD_GLUCOSE,
            DataTypes.BODY_COMPOSITION, DataTypes.EXERCISE,
        )
        val PERMISSIONS: Set<Permission> = READ_TYPES.map { Permission.of(it, AccessType.READ) }.toSet()
    }

    suspend fun grantedPermissions(): Set<Permission> = store.getGrantedPermissions(PERMISSIONS)

    /** Affiche l'écran d'autorisation Samsung Health ; renvoie les permissions accordées. */
    suspend fun requestPermissions(activity: Activity): Set<Permission> =
        store.requestPermissions(PERMISSIONS, activity)

    suspend fun readAll(): Map<String, Float> {
        val granted = grantedPermissions().map { it.dataType }.toSet()
        val out = linkedMapOf<String, Float>()
        val today = LocalDate.now()
        val now = LocalDateTime.now()
        val sinceMidnight = LocalTimeFilter.of(today.atStartOfDay(), now)
        val todayOnly = LocalDateFilter.of(today, today.plusDays(1))

        suspend fun read(type: DataType, block: suspend () -> Unit) {
            if (type !in granted) return
            try {
                block()
            } catch (e: Exception) {
                Log.w(TAG, "Lecture ${type.name} impossible", e)
            }
        }

        suspend fun <T : Any> aggregate(request: AggregateRequest<T>): T? =
            store.aggregateData(request).dataList.firstOrNull()?.value

        /** Dernières mesures sur [days] jours, la plus récente d'abord. */
        suspend fun latest(builder: ReadDataRequest.DualTimeBuilder<HealthDataPoint>, days: Long, limit: Int = 1) =
            store.readData(
                builder.setLocalTimeFilter(LocalTimeFilter.of(now.minusDays(days), now))
                    .setOrdering(Ordering.DESC).setLimit(limit).build()
            ).dataList

        fun put(key: String, v: Number?) {
            if (v != null) out[key] = v.toFloat()
        }

        // --- Scores ---
        read(DataTypes.ENERGY_SCORE) {
            val p = store.readData(
                DataTypes.ENERGY_SCORE.readDataRequestBuilder
                    .setLocalDateFilter(LocalDateFilter.of(today.minusDays(1), today.plusDays(1)))
                    .setOrdering(Ordering.DESC).setLimit(1).build()
            ).dataList.firstOrNull()
            put(Keys.ENERGY, p?.getValue(DataType.EnergyScoreType.ENERGY_SCORE))
        }
        read(DataTypes.SLEEP) {
            // Une journée peut compter plusieurs sommeils (nuit + sieste), chacun avec son propre
            // score. Samsung Health affiche le score de la nuit (la période la plus longue) : la
            // sieste, plus récente, ne doit pas le remplacer [vu sur la montre : 36 au lieu de 54].
            val recent = latest(DataTypes.SLEEP.readDataRequestBuilder, days = 2, limit = 10)
            fun wakeDate(p: HealthDataPoint): LocalDate? =
                p.endTime?.let { LocalDateTime.ofInstant(it, p.zoneOffset ?: ZoneId.systemDefault()).toLocalDate() }
            val day = recent.firstOrNull()?.let(::wakeDate)
            val sameDay = recent.filter { wakeDate(it) == day }
            fun length(p: HealthDataPoint): Duration =
                p.getValue(DataType.SleepType.DURATION) ?: Duration.between(p.startTime, p.endTime)
            val night = sameDay.maxByOrNull { length(it) }
            put(Keys.SLEEP_SCORE, night?.getValue(DataType.SleepType.SLEEP_SCORE))
            // Durée réelle (comme « Durée réelle de sommeil » de Samsung Health) : toutes les
            // phases sauf l'éveil, nuit et siestes du jour ; à défaut, durée des enregistrements.
            val asleep = sameDay.sumOf { p ->
                val stages = p.getValue(DataType.SleepType.SESSIONS).orEmpty().flatMap { it.stages.orEmpty() }
                if (stages.isEmpty()) length(p).toMinutes()
                else stages.filter { it.stage != DataType.SleepType.StageType.AWAKE }
                    .sumOf { Duration.between(it.startTime, it.endTime).toMinutes() }
            }
            put(Keys.SLEEP_MIN, asleep.takeIf { it > 0 })
        }
        read(DataTypes.SLEEP_GOAL) {
            val bed = aggregate(DataType.SleepGoalType.LAST_BED_TIME.requestBuilder.setLocalDateFilter(todayOnly).build())
            val wake = aggregate(DataType.SleepGoalType.LAST_WAKE_UP_TIME.requestBuilder.setLocalDateFilter(todayOnly).build())
            if (bed != null && wake != null) {
                var minutes = Duration.between(bed, wake).toMinutes()
                if (minutes <= 0) minutes += 24 * 60   // coucher la veille
                put(Keys.SLEEP_GOAL_MIN, minutes)
            }
        }

        // --- Activité du jour ---
        read(DataTypes.STEPS) {
            put(Keys.STEPS, aggregate(DataType.StepsType.TOTAL.requestBuilder.setLocalTimeFilter(sinceMidnight).build()))
        }
        read(DataTypes.STEPS_GOAL) {
            put(Keys.STEPS_GOAL, aggregate(DataType.StepsGoalType.LAST.requestBuilder.setLocalDateFilter(todayOnly).build()))
        }
        read(DataTypes.ACTIVITY_SUMMARY) {
            put(Keys.DISTANCE_M, aggregate(DataType.ActivitySummaryType.TOTAL_DISTANCE.requestBuilder
                .setLocalTimeFilter(sinceMidnight).build()))
            put(Keys.ACTIVE_KCAL, aggregate(DataType.ActivitySummaryType.TOTAL_ACTIVE_CALORIES_BURNED.requestBuilder
                .setLocalTimeFilter(sinceMidnight).build()))
            put(Keys.TOTAL_KCAL, aggregate(DataType.ActivitySummaryType.TOTAL_CALORIES_BURNED.requestBuilder
                .setLocalTimeFilter(sinceMidnight).build()))
            put(Keys.ACTIVE_MIN, aggregate(DataType.ActivitySummaryType.TOTAL_ACTIVE_TIME.requestBuilder
                .setLocalTimeFilter(sinceMidnight).build())?.toMinutes())
        }
        read(DataTypes.ACTIVE_CALORIES_BURNED_GOAL) {
            put(Keys.ACTIVE_KCAL_GOAL, aggregate(DataType.ActiveCaloriesBurnedGoalType.LAST.requestBuilder
                .setLocalDateFilter(todayOnly).build()))
        }
        read(DataTypes.ACTIVE_TIME_GOAL) {
            put(Keys.ACTIVE_MIN_GOAL, aggregate(DataType.ActiveTimeGoalType.LAST.requestBuilder
                .setLocalDateFilter(todayOnly).build())?.toMinutes())
        }
        read(DataTypes.FLOORS_CLIMBED) {
            put(Keys.FLOORS, aggregate(DataType.FloorsClimbedType.TOTAL.requestBuilder.setLocalTimeFilter(sinceMidnight).build()))
        }

        // --- Alimentation, eau ---
        read(DataTypes.WATER_INTAKE) {
            put(Keys.WATER_ML, aggregate(DataType.WaterIntakeType.TOTAL.requestBuilder.setLocalTimeFilter(sinceMidnight).build()))
        }
        read(DataTypes.WATER_INTAKE_GOAL) {
            put(Keys.WATER_GOAL_ML, aggregate(DataType.WaterIntakeGoalType.LAST.requestBuilder.setLocalDateFilter(todayOnly).build()))
        }
        read(DataTypes.NUTRITION) {
            put(Keys.FOOD_KCAL, aggregate(DataType.NutritionType.TOTAL_CALORIES.requestBuilder.setLocalTimeFilter(sinceMidnight).build()))
        }
        read(DataTypes.NUTRITION_GOAL) {
            put(Keys.FOOD_KCAL_GOAL, aggregate(DataType.NutritionGoalType.LAST_CALORIES.requestBuilder
                .setLocalDateFilter(todayOnly).build()))
        }

        // --- Mesures ---
        read(DataTypes.HEART_RATE) {
            put(Keys.HR_LAST, latest(DataTypes.HEART_RATE.readDataRequestBuilder, days = 1).firstOrNull()
                ?.getValue(DataType.HeartRateType.HEART_RATE))
            put(Keys.HR_MIN, aggregate(DataType.HeartRateType.MIN.requestBuilder.setLocalDateFilter(todayOnly).build()))
            put(Keys.HR_MAX, aggregate(DataType.HeartRateType.MAX.requestBuilder.setLocalDateFilter(todayOnly).build()))
        }
        read(DataTypes.BLOOD_OXYGEN) {
            put(Keys.SPO2, latest(DataTypes.BLOOD_OXYGEN.readDataRequestBuilder, days = 7).firstOrNull()
                ?.getValue(DataType.BloodOxygenType.OXYGEN_SATURATION))
        }
        read(DataTypes.SKIN_TEMPERATURE) {
            put(Keys.SKIN_TEMP, latest(DataTypes.SKIN_TEMPERATURE.readDataRequestBuilder, days = 7).firstOrNull()
                ?.getValue(DataType.SkinTemperatureType.SKIN_TEMPERATURE))
        }
        read(DataTypes.BODY_TEMPERATURE) {
            put(Keys.BODY_TEMP, latest(DataTypes.BODY_TEMPERATURE.readDataRequestBuilder, days = 30).firstOrNull()
                ?.getValue(DataType.BodyTemperatureType.BODY_TEMPERATURE))
        }
        read(DataTypes.BLOOD_PRESSURE) {
            val p = latest(DataTypes.BLOOD_PRESSURE.readDataRequestBuilder, days = 90).firstOrNull()
            put(Keys.BP_SYS, p?.getValue(DataType.BloodPressureType.SYSTOLIC))
            put(Keys.BP_DIA, p?.getValue(DataType.BloodPressureType.DIASTOLIC))
        }
        read(DataTypes.BLOOD_GLUCOSE) {
            put(Keys.GLUCOSE, latest(DataTypes.BLOOD_GLUCOSE.readDataRequestBuilder, days = 30).firstOrNull()
                ?.getValue(DataType.BloodGlucoseType.GLUCOSE_LEVEL))
        }
        read(DataTypes.BODY_COMPOSITION) {
            val p = latest(DataTypes.BODY_COMPOSITION.readDataRequestBuilder, days = 365).firstOrNull()
            put(Keys.WEIGHT, p?.getValue(DataType.BodyCompositionType.WEIGHT))
            put(Keys.BODY_FAT, p?.getValue(DataType.BodyCompositionType.BODY_FAT))
            put(Keys.MUSCLE, p?.getValue(DataType.BodyCompositionType.SKELETAL_MUSCLE_MASS))
            put(Keys.BMI, p?.getValue(DataType.BodyCompositionType.BODY_MASS_INDEX))
        }

        // --- Dernière séance d'exercice ---
        read(DataTypes.EXERCISE) {
            val sessions = latest(DataTypes.EXERCISE.readDataRequestBuilder, days = 60, limit = 20)
                .flatMap { it.getValue(DataType.ExerciseType.SESSIONS).orEmpty() }
                .sortedByDescending { it.startTime }
            sessions.firstOrNull()?.let { last ->
                put(Keys.LAST_EX_MIN, last.duration.toMinutes())
                put(Keys.LAST_EX_M, last.distance)
            }
            put(Keys.VO2MAX, sessions.firstNotNullOfOrNull { it.vo2Max })
        }

        return out
    }
}
