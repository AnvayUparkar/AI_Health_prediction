package com.originhealth.app.sync

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.originhealth.app.health.HealthConnectManager
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class HealthDataSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    private val healthConnectManager = HealthConnectManager(appContext)
    private val client = OkHttpClient()
    private val apiBaseUrl = "http://your-server-ip:5000" // Replace with production URL

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            if (!healthConnectManager.hasAllPermissions()) {
                return@withContext Result.failure()
            }

            // 1. Gather real data from Health Connect
            val steps = healthConnectManager.getDailySteps()
            val heartRate = healthConnectManager.getAverageHeartRate()
            val sleepHours = healthConnectManager.getSleepDurationHours()

            // 2. Prepare payload
            val json = JSONObject().apply {
                put("steps", steps)
                put("avg_heart_rate", heartRate)
                put("sleep_hours", sleepHours)
            }

            // 3. Send to Backend
            val token = "Bearer YOUR_JWT_TOKEN" // Pull this from EncryptedSharedPreferences
            val requestBody = json.toString().toRequestBody("application/json".toMediaType())
            
            val request = Request.Builder()
                .url("$apiBaseUrl/api/health-analysis")
                .post(requestBody)
                .addHeader("Authorization", token)
                .build()

            val response = client.newCall(request).execute()
            
            if (response.isSuccessful) {
                Result.success()
            } else {
                Result.retry()
            }
        } catch (e: Exception) {
            Result.retry()
        }
    }
}
