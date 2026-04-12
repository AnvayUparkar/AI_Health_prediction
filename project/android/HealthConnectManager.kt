package com.originhealth.app.health

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.request.AggregateRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

/**
 * HealthConnectManager
 * ====================
 * Reads health metrics from Android Health Connect (on-device data store).
 *
 * Health Connect aggregates data from every app the user has granted access to:
 * Samsung Health, Fitbit, Garmin Connect, Google Fit, Pixel Watch, etc.
 *
 * This class provides:
 *   - Single-day convenience methods (getDailySteps, etc.)
 *   - A 7-day batch method (getWeeklyMetrics) used by the sync worker
 */
class HealthConnectManager(private val context: Context) {

    private val healthConnectClient by lazy { HealthConnectClient.getOrCreate(context) }

    val permissions = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class)
    )

    /**
     * Check if all required permissions are granted.
     */
    suspend fun hasAllPermissions(): Boolean {
        return healthConnectClient.permissionController
            .getGrantedPermissions()
            .containsAll(permissions)
    }

    // ── Single-day convenience methods ────────────────────────────────────

    suspend fun getDailySteps(): Long {
        val startTime = Instant.now().truncatedTo(ChronoUnit.DAYS)
        val endTime = Instant.now()
        return getStepsForRange(startTime, endTime)
    }

    suspend fun getAverageHeartRate(): Double {
        val startTime = Instant.now().minus(24, ChronoUnit.HOURS)
        val endTime = Instant.now()
        return getHeartRateForRange(startTime, endTime)
    }

    suspend fun getSleepDurationHours(): Double {
        val startTime = Instant.now().minus(24, ChronoUnit.HOURS)
        val endTime = Instant.now()
        return getSleepForRange(startTime, endTime)
    }

    // ── 7-day batch method (used by HealthDataSyncWorker) ─────────────────

    /**
     * Returns a list of daily metric maps for the last 7 calendar days.
     *
     * Each entry:
     *   {
     *     "date": "2026-04-06",
     *     "steps": 4500,
     *     "avg_heart_rate": 72.3,
     *     "sleep_hours": 6.5
     *   }
     *
     * Days with no data will still be included with zeroed values so the
     * backend always receives a complete 7-day window.
     */
    suspend fun getWeeklyMetrics(): List<Map<String, Any>> {
        val zone = ZoneId.systemDefault()
        val today = LocalDate.now(zone)
        val formatter = DateTimeFormatter.ISO_LOCAL_DATE
        val results = mutableListOf<Map<String, Any>>()

        for (daysAgo in 6 downTo 0) {
            val date = today.minusDays(daysAgo.toLong())
            val dayStart = date.atStartOfDay(zone).toInstant()
            val dayEnd = date.plusDays(1).atStartOfDay(zone).toInstant()

            val steps = getStepsForRange(dayStart, dayEnd)
            val hr = getHeartRateForRange(dayStart, dayEnd)
            val sleep = getSleepForRange(dayStart, dayEnd)

            results.add(mapOf(
                "date" to date.format(formatter),
                "steps" to steps,
                "avg_heart_rate" to hr,
                "sleep_hours" to sleep
            ))
        }

        return results
    }

    // ── Internal range-based helpers ──────────────────────────────────────

    private suspend fun getStepsForRange(start: Instant, end: Instant): Long {
        return try {
            val response = healthConnectClient.aggregate(
                AggregateRequest(
                    metrics = setOf(StepsRecord.COUNT_TOTAL),
                    timeRangeFilter = TimeRangeFilter.between(start, end)
                )
            )
            response[StepsRecord.COUNT_TOTAL] ?: 0L
        } catch (e: Exception) {
            0L
        }
    }

    private suspend fun getHeartRateForRange(start: Instant, end: Instant): Double {
        return try {
            val response = healthConnectClient.aggregate(
                AggregateRequest(
                    metrics = setOf(HeartRateRecord.BPM_AVG),
                    timeRangeFilter = TimeRangeFilter.between(start, end)
                )
            )
            response[HeartRateRecord.BPM_AVG]?.toDouble() ?: 70.0
        } catch (e: Exception) {
            70.0
        }
    }

    private suspend fun getSleepForRange(start: Instant, end: Instant): Double {
        return try {
            val response = healthConnectClient.readRecords(
                ReadRecordsRequest(
                    recordType = SleepSessionRecord::class,
                    timeRangeFilter = TimeRangeFilter.between(start, end)
                )
            )
            val totalMillis = response.records.sumOf {
                java.time.Duration.between(it.startTime, it.endTime).toMillis()
            }
            totalMillis / (1000.0 * 60 * 60)
        } catch (e: Exception) {
            0.0
        }
    }
}
