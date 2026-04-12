package com.originhealth.app.sync

import android.content.Context
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import androidx.work.*
import com.originhealth.app.health.HealthConnectManager
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.TimeZone
import java.util.concurrent.TimeUnit

/**
 * HealthDataSyncWorker
 * ====================
 * WorkManager periodic task that:
 *   1. Reads 7 days of metrics from Health Connect (on-device)
 *   2. POSTs them to the backend `/api/health-connect-sync` endpoint
 *   3. Retries with exponential backoff on failure
 *
 * This acts as the FALLBACK data pipeline when Google Fit REST API is unavailable.
 *
 * Schedule this worker from your Application.onCreate() or MainActivity:
 *   HealthDataSyncWorker.schedulePeriodicSync(applicationContext)
 */
class HealthDataSyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    companion object {
        private const val TAG = "HealthDataSync"
        private const val WORK_NAME = "health_connect_sync"
        private const val PREFS_FILE = "secure_prefs"
        private const val KEY_JWT_TOKEN = "jwt_token"
        private const val KEY_API_BASE_URL = "api_base_url"
        private const val DEFAULT_API_URL = "http://10.0.2.2:5000" // Android emulator -> host

        /**
         * Schedule a periodic sync every 4 hours with network constraint.
         * Uses KEEP policy so re-calling is safe (won't duplicate).
         */
        fun schedulePeriodicSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val syncRequest = PeriodicWorkRequestBuilder<HealthDataSyncWorker>(
                4, TimeUnit.HOURS,
                30, TimeUnit.MINUTES  // flex window
            )
                .setConstraints(constraints)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                syncRequest
            )

            Log.i(TAG, "Periodic Health Connect sync scheduled (every 4h)")
        }

        /**
         * Trigger an immediate one-shot sync (e.g. when user taps "Sync Now").
         */
        fun triggerImmediateSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val syncRequest = OneTimeWorkRequestBuilder<HealthDataSyncWorker>()
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                "${WORK_NAME}_immediate",
                ExistingWorkPolicy.REPLACE,
                syncRequest
            )

            Log.i(TAG, "Immediate Health Connect sync triggered")
        }
    }

    private val healthConnectManager = HealthConnectManager(applicationContext)
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)  // Gemini analysis can be slow
        .build()

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        Log.i(TAG, "Starting Health Connect sync...")

        // 1. Check permissions
        if (!healthConnectManager.hasAllPermissions()) {
            Log.w(TAG, "Missing Health Connect permissions — aborting")
            return@withContext Result.failure(
                workDataOf("error" to "Missing Health Connect permissions")
            )
        }

        // 2. Read JWT token from EncryptedSharedPreferences
        val token = getJwtToken()
        if (token.isNullOrBlank()) {
            Log.w(TAG, "No JWT token found — user must log in first")
            return@withContext Result.failure(
                workDataOf("error" to "User not authenticated")
            )
        }

        // 3. Gather 7 days of metrics from Health Connect
        val weeklyMetrics = try {
            healthConnectManager.getWeeklyMetrics()
        } catch (e: Exception) {
            Log.e(TAG, "Failed to read Health Connect data", e)
            return@withContext Result.retry()
        }

        if (weeklyMetrics.isEmpty()) {
            Log.w(TAG, "No Health Connect data available")
            return@withContext Result.failure(
                workDataOf("error" to "No health data available")
            )
        }

        Log.i(TAG, "Read ${weeklyMetrics.size} day(s) from Health Connect")

        // 4. Build JSON payload
        val jsonArray = JSONArray()
        for (day in weeklyMetrics) {
            jsonArray.put(JSONObject().apply {
                put("date", day["date"])
                put("steps", day["steps"])
                put("avg_heart_rate", day["avg_heart_rate"])
                put("sleep_hours", day["sleep_hours"])
            })
        }

        val payload = JSONObject().apply {
            put("daily_metrics", jsonArray)
            put("timezone_offset", TimeZone.getDefault().rawOffset / 60000) // ms -> min
        }

        // 5. POST to backend
        val apiUrl = getApiBaseUrl()
        val requestBody = payload.toString().toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("$apiUrl/api/health-connect-sync")
            .post(requestBody)
            .addHeader("Authorization", "Bearer $token")
            .addHeader("Content-Type", "application/json")
            .build()

        return@withContext try {
            val response = client.newCall(request).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                Log.i(TAG, "Sync successful: $body")
                Result.success(workDataOf("response" to body))
            } else if (response.code == 401) {
                Log.w(TAG, "JWT expired — user needs to re-authenticate")
                Result.failure(workDataOf("error" to "Authentication expired"))
            } else {
                Log.w(TAG, "Server error ${response.code}: $body")
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error during sync", e)
            Result.retry()
        }
    }

    private fun getJwtToken(): String? {
        return try {
            val masterKey = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
            val prefs = EncryptedSharedPreferences.create(
                PREFS_FILE,
                masterKey,
                applicationContext,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
            prefs.getString(KEY_JWT_TOKEN, null)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to read JWT from EncryptedSharedPreferences", e)
            null
        }
    }

    private fun getApiBaseUrl(): String {
        return try {
            val masterKey = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
            val prefs = EncryptedSharedPreferences.create(
                PREFS_FILE,
                masterKey,
                applicationContext,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
            prefs.getString(KEY_API_BASE_URL, DEFAULT_API_URL) ?: DEFAULT_API_URL
        } catch (e: Exception) {
            DEFAULT_API_URL
        }
    }
}
