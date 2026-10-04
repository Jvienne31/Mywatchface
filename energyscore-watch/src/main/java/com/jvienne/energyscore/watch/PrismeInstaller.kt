package com.jvienne.energyscore.watch

import android.content.Context
import android.os.Build
import android.os.ParcelFileDescriptor
import androidx.wear.watchfacepush.WatchFacePushManager
import androidx.wear.watchfacepush.WatchFacePushManagerFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/**
 * Installe et met à jour le cadran Prisme sans adb, par Watch Face Push (Wear OS 6 et plus).
 *
 * La CI embarque dans les assets l'APK de la variante « push » de Prisme (paquet
 * [PACKAGE], imposé par l'API : <appli>.watchfacepush.<cadran>) et son jeton de validation
 * délivré par l'outil officiel de Google.
 */
object PrismeInstaller {
    const val PACKAGE = "com.jvienne.santesync.watchfacepush.prisme"
    const val PERMISSION_ACTIVATE = "com.google.wear.permission.SET_PUSHED_WATCH_FACE_AS_ACTIVE"
    private const val APK_ASSET = "prisme.apk"
    private const val TOKEN_ASSET = "prisme_token.txt"

    /** État affiché à l'écran. */
    data class State(
        val bundledVersion: Long,
        val installedVersion: Long?,
        val slotId: String?,
        val active: Boolean,
    ) {
        val needsInstall get() = installedVersion == null
        val needsUpdate get() = installedVersion != null && installedVersion < bundledVersion
    }

    /** Watch Face Push existe sur la montre et l'appli embarque bien le cadran. */
    fun supported(context: Context): Boolean =
        Build.VERSION.SDK_INT >= 36 && context.assets.list("")?.contains(APK_ASSET) == true

    suspend fun state(context: Context): State = withContext(Dispatchers.IO) {
        val apk = bundledApk(context)
        val bundled = context.packageManager.getPackageArchiveInfo(apk.path, 0)?.longVersionCode ?: 0L
        val manager = manager(context)
        val face = manager.listWatchFaces().installedWatchFaceDetails.firstOrNull { it.packageName == PACKAGE }
        State(
            bundledVersion = bundled,
            installedVersion = face?.versionCode,
            slotId = face?.slotId,
            active = face != null && manager.isWatchFaceActive(PACKAGE),
        )
    }

    /** Installe Prisme ou le met à jour ; renvoie le message à afficher. */
    suspend fun installOrUpdate(context: Context): String = withContext(Dispatchers.IO) {
        val manager = manager(context)
        val token = context.assets.open(TOKEN_ASSET).bufferedReader().use { it.readText().trim() }
        val current = state(context)
        ParcelFileDescriptor.open(bundledApk(context), ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
            try {
                if (current.needsInstall) {
                    manager.addWatchFace(fd, token)
                    "Prisme installé"
                } else {
                    manager.updateWatchFace(current.slotId!!, fd, token)
                    "Prisme mis à jour"
                }
            } catch (e: WatchFacePushManager.AddWatchFaceException) {
                "Installation refusée : ${e.message}"
            } catch (e: WatchFacePushManager.UpdateWatchFaceException) {
                "Mise à jour refusée : ${e.message}"
            }
        }
    }

    /** Met Prisme comme cadran actif (demande l'autorisation dédiée, sinon choix manuel). */
    suspend fun activate(context: Context): String = withContext(Dispatchers.IO) {
        val slot = state(context).slotId ?: return@withContext "Prisme n'est pas installé"
        try {
            manager(context).setWatchFaceAsActive(slot)
            "Prisme est le cadran actif"
        } catch (e: WatchFacePushManager.SetWatchFaceAsActiveException) {
            "Activation impossible : appui long sur le cadran pour choisir Prisme"
        }
    }

    private fun manager(context: Context) = WatchFacePushManagerFactory.createWatchFacePushManager(context)

    /** Copie l'APK embarqué dans le cache (lisible par PackageManager et ouvrable en fichier). */
    private fun bundledApk(context: Context): File {
        val file = File(context.cacheDir, APK_ASSET)
        context.assets.open(APK_ASSET).use { input -> file.outputStream().use { input.copyTo(it) } }
        return file
    }
}
