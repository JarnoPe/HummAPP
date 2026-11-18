package fi.hummapp.android.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import com.google.gson.JsonParser
import fi.hummapp.android.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Uusin julkaistu sovellusversio GitHubin Releases-sivulta. */
data class AppUpdate(
    val versionCode: Int,
    val versionName: String,
    val apkUrl: String,
    val apkSizeBytes: Long
)

/**
 * Tarkistaa, onko GitHubiin julkaistu uudempi APK, lataa sen ja avaa Androidin asentajan.
 *
 * Julkaisut tekee .github/workflows/android.yml: tagi on muotoa `android-v<versionCode>`
 * ja julkaisun liitteenä on yksi .apk-tiedosto. Asennus vaatii käyttäjän hyväksynnän,
 * ja Android asentaa päivityksen vain, jos se on allekirjoitettu samalla avaimella.
 */
object AppUpdater {

    private const val TAG_PREFIX = "android-v"
    private val latestUrl = "https://api.github.com/repos/${BuildConfig.UPDATE_REPO}/releases/latest"

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    val currentVersionName: String get() = BuildConfig.VERSION_NAME

    /** Palauttaa uudemman version tiedot tai null, jos sovellus on ajan tasalla tai tarkistus ei onnistu. */
    suspend fun checkForUpdate(): AppUpdate? = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder()
                .url(latestUrl)
                .header("Accept", "application/vnd.github+json")
                .build()
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return@use null
                val json = JsonParser.parseString(response.body?.string().orEmpty()).asJsonObject
                val tag = json.get("tag_name")?.asString.orEmpty()
                if (!tag.startsWith(TAG_PREFIX)) return@use null
                val code = tag.removePrefix(TAG_PREFIX).toIntOrNull() ?: return@use null
                if (code <= BuildConfig.VERSION_CODE) return@use null

                val apk = json.getAsJsonArray("assets")
                    ?.map { it.asJsonObject }
                    ?.firstOrNull { it.get("name")?.asString?.endsWith(".apk") == true }
                    ?: return@use null

                AppUpdate(
                    versionCode = code,
                    versionName = "1.3.$code",
                    apkUrl = apk.get("browser_download_url").asString,
                    apkSizeBytes = apk.get("size")?.asLong ?: -1L
                )
            }
        }.getOrNull()
    }

    /** Lataa APK:n sovelluksen välimuistiin. onProgress saa arvoja 0..1. */
    suspend fun download(
        context: Context,
        update: AppUpdate,
        onProgress: (Float) -> Unit
    ): File = withContext(Dispatchers.IO) {
        val dir = File(context.cacheDir, "updates").apply { mkdirs() }
        dir.listFiles()?.forEach { it.delete() }
        val target = File(dir, "hummapp-${update.versionCode}.apk")

        val request = Request.Builder().url(update.apkUrl).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
            val body = response.body ?: throw IOException("Tyhjä vastaus")
            val total = body.contentLength().takeIf { it > 0 } ?: update.apkSizeBytes
            body.byteStream().use { input ->
                target.outputStream().use { output ->
                    val buffer = ByteArray(64 * 1024)
                    var read: Int
                    var done = 0L
                    while (input.read(buffer).also { read = it } != -1) {
                        output.write(buffer, 0, read)
                        done += read
                        if (total > 0) onProgress((done.toFloat() / total).coerceIn(0f, 1f))
                    }
                }
            }
        }
        target
    }

    /** Onko käyttäjä sallinut HummAPPin asentaa sovelluksia (Android 8+). */
    fun canInstall(context: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.O || context.packageManager.canRequestPackageInstalls()

    /** Avaa asetuksen, jossa käyttäjä sallii HummAPPin asentaa päivityksiä. */
    fun openInstallPermissionSettings(context: Context) {
        val intent = Intent(
            Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
            Uri.parse("package:${context.packageName}")
        ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }

    /** Avaa Androidin asentajan ladatulle APK:lle. */
    fun install(context: Context, apk: File) {
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.updates", apk)
        val intent = Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }
}
