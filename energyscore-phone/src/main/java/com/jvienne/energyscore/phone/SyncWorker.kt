package com.jvienne.energyscore.phone

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

/** Synchronisation automatique en arrière-plan, toutes les 30 minutes. */
class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = try {
        WatchSync.run(applicationContext)
        Result.success()
    } catch (e: Exception) {
        Log.w("SyncWorker", "Synchronisation échouée", e)
        Result.retry()
    }

    companion object {
        fun schedule(context: Context) {
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                "sante_sync",
                ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<SyncWorker>(30, TimeUnit.MINUTES).build(),
            )
        }
    }
}
