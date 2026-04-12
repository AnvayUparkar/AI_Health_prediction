# Android Health Connect Integration Guide (Kotlin)

This document provides the necessary logic to fetch health data from **Health Connect** and send it to the new `/api/health-analysis` endpoint in your backend.

---

## 1. Dependencies
Add the following to your `build.gradle` (Module: app):

```kotlin
dependencies {
    implementation("androidx.health.connect:connect-client:1.1.0-alpha11")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
}
```

---

## 2. API Interface
Define the Retrofit interface for the backend:

```kotlin
interface HealthApiService {
    @POST("api/health-analysis")
    suspend fun sendHealthData(@Body data: HealthRequest): HealthResponse
}

data class HealthRequest(
    val steps: Int,
    val avg_heart_rate: Float,
    val sleep_hours: Float
)

data class HealthResponse(
    val success: Boolean,
    val data: HealthAnalysisData
)

data class HealthAnalysisData(
    val health_score: Int,
    val risk_level: String,
    val health_status: String,
    val diet_plan: List<String>,
    val recommendations: List<String>
)
```

---

## 3. Data Extraction Logic
Snippet to fetch data from Health Connect and send it to the backend:

```kotlin
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Instant
import java.time.temporal.ChronoUnit

class HealthDataSync(private val healthConnectClient: HealthConnectClient) {

    suspend fun syncHealthData() {
        val endTime = Instant.now()
        val startTime = endTime.minus(1, ChronoUnit.DAYS)
        val timeRangeFilter = TimeRangeFilter.between(startTime, endTime)

        // 1. Fetch Steps
        val stepsRequest = ReadRecordsRequest(
            recordType = StepsRecord::class,
            timeRangeFilter = timeRangeFilter
        )
        val steps = healthConnectClient.readRecords(stepsRequest).records.sumOf { it.count }.toInt()

        // 2. Fetch Heart Rate
        val heartRateRequest = ReadRecordsRequest(
            recordType = HeartRateRecord::class,
            timeRangeFilter = timeRangeFilter
        )
        val heartRateRecords = healthConnectClient.readRecords(heartRateRequest).records
        val avgHeartRate = if (heartRateRecords.isNotEmpty()) {
            heartRateRecords.flatMap { it.samples }.map { it.beatsPerMinute }.average().toFloat()
        } else 0f

        // 3. Fetch Sleep
        val sleepRequest = ReadRecordsRequest(
            recordType = SleepSessionRecord::class,
            timeRangeFilter = timeRangeFilter
        )
        val sleepRecords = healthConnectClient.readRecords(sleepRequest).records
        val sleepHours = if (sleepRecords.isNotEmpty()) {
            sleepRecords.sumOf { 
                ChronoUnit.SECONDS.between(it.startTime, it.endTime) 
            } / 3600f
        } else 0f

        // 4. Send to Backend
        val request = HealthRequest(steps, avgHeartRate, sleepHours)
        val response = RetrofitClient.apiService.sendHealthData(request)
        
        if (response.success) {
            // Handle success (UI update)
        }
    }
}
```

---

## 4. Permissions
Ensure you have requested permissions for:
- `HealthPermission.getReadPermission(StepsRecord::class)`
- `HealthPermission.getReadPermission(HeartRateRecord::class)`
- `HealthPermission.getReadPermission(SleepSessionRecord::class)`
