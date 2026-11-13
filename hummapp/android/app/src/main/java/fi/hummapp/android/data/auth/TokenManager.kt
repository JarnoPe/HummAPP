package fi.hummapp.android.data.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class TokenManager(context: Context) {

    private val prefs: SharedPreferences = try {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            "hummapp_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (e: Exception) {
        context.getSharedPreferences("hummapp_prefs", Context.MODE_PRIVATE)
    }

    companion object {
        private const val KEY_TOKEN = "access_token"
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_USERNAME = "username"
        private const val KEY_ROLE = "role"

        // Tämän live-ympäristön osoite (esikonfiguroitu valmiiksi)
        const val ENV_SHARED_URL = "https://ais-pre-jjufdm4idfqg3xxnq6pytl-1003724038923.europe-west2.run.app"
        const val ENV_DEV_URL = "https://ais-dev-jjufdm4idfqg3xxnq6pytl-1003724038923.europe-west2.run.app"
        const val NAS_DEFAULT_URL = "http://192.168.1.100:8000"
        const val DEFAULT_BASE_URL = ENV_SHARED_URL
    }

    fun saveAuth(token: String, username: String, role: String) {
        prefs.edit()
            .putString(KEY_TOKEN, token)
            .putString(KEY_USERNAME, username)
            .putString(KEY_ROLE, role)
            .apply()
    }

    fun saveBaseUrl(url: String) {
        val cleaned = url.trim().let { if (it.endsWith("/")) it.dropLast(1) else it }
        prefs.edit().putString(KEY_BASE_URL, cleaned).apply()
    }

    fun getBaseUrl(): String {
        return prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
    }

    fun getToken(): String? {
        return prefs.getString(KEY_TOKEN, null)
    }

    fun getUsername(): String? {
        return prefs.getString(KEY_USERNAME, null)
    }

    fun getRole(): String? {
        return prefs.getString(KEY_ROLE, null)
    }

    fun clear() {
        prefs.edit()
            .remove(KEY_TOKEN)
            .remove(KEY_USERNAME)
            .remove(KEY_ROLE)
            .apply()
    }

    fun isLoggedIn(): Boolean = !getToken().isNullOrBlank()
}
