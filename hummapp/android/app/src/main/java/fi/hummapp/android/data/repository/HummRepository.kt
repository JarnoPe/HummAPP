package fi.hummapp.android.data.repository

import com.google.gson.Gson
import fi.hummapp.android.data.api.HummApiService
import fi.hummapp.android.data.auth.TokenManager
import fi.hummapp.android.data.model.*
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.*

class HummRepository(
    private val tokenManager: TokenManager
) {
    private var api: HummApiService = HummApiService.create(tokenManager)
    private val gson = Gson()

    fun refreshApi() {
        api = HummApiService.create(tokenManager)
    }

    private fun parseErrorDetail(rawError: String?, fallback: String): String {
        if (rawError.isNullOrBlank()) return fallback
        return try {
            val json = JSONObject(rawError)
            json.optString("detail", fallback)
        } catch (_: Exception) {
            rawError
        }
    }

    suspend fun checkHealth(): Result<HealthResponse> {
        return try {
            val resp = api.getHealth()
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Palvelin vastasi virheellä ${resp.code()}"))
        } catch (e: Exception) {
            Result.failure(Exception("Yhteysvirhe: ${e.localizedMessage ?: "Palvelin ei vastaa"}"))
        }
    }

    suspend fun getSystemStatus(): Result<SystemStatus> {
        return try {
            val resp = api.getSystemStatus()
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Järjestelmätilan haku epäonnistui (${resp.code()})"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun login(username: String, password: String): Result<TokenResponse> {
        return try {
            val resp = api.login(LoginRequest(username, password))
            if (resp.isSuccessful && resp.body() != null) {
                val token = resp.body()!!
                tokenManager.saveAuth(token.accessToken, token.username, token.role)
                refreshApi()
                Result.success(token)
            } else {
                val msg = parseErrorDetail(resp.errorBody()?.string(), "Kirjautuminen epäonnistui (${resp.code()})")
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(Exception("Verkkovirhe: ${e.localizedMessage ?: "Tarkista palvelimen osoite"}"))
        }
    }

    suspend fun getHorses(): Result<List<Horse>> {
        return try {
            val resp = api.getHorses()
            if (resp.isSuccessful) Result.success(resp.body() ?: emptyList())
            else Result.failure(Exception("Hevosten haku epäonnistui: ${resp.code()}"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun createHorse(
        name: String,
        breed: String? = null,
        birthYear: Int? = null,
        ownerName: String? = null,
        stallBox: String? = null,
        description: String? = null
    ): Result<Horse> {
        return try {
            val resp = api.createHorse(
                HorseCreateRequest(
                    name = name,
                    breed = breed,
                    birthYear = birthYear,
                    ownerName = ownerName,
                    stallBox = stallBox,
                    description = description
                )
            )
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception(parseErrorDetail(resp.errorBody()?.string(), "Hevosen lisäys epäonnistui")))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateHorse(
        id: Int,
        request: HorseUpdateRequest
    ): Result<Horse> {
        return try {
            val resp = api.updateHorse(id, request)
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception(parseErrorDetail(resp.errorBody()?.string(), "Hevosen tietojen päivitys epäonnistui")))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun assignNfcTag(horseId: Int, nfcUid: String): Result<NfcTag> {
        return try {
            val resp = api.assignNfcTag(horseId, AssignNfcTagRequest(nfcUid))
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception(parseErrorDetail(resp.errorBody()?.string(), "Tagin yhdistäminen epäonnistui")))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getNfcEvents(limit: Int = 50): Result<List<NfcEventResponse>> {
        return try {
            val resp = api.getNfcEvents(limit)
            if (resp.isSuccessful) Result.success(resp.body() ?: emptyList())
            else Result.failure(Exception("NFC-tapahtumien haku epäonnistui: ${resp.code()}"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun sendNfcEvent(nfcUid: String, location: String = "kuvausalue-1"): Result<NfcEventResponse> {
        return try {
            val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
            sdf.timeZone = TimeZone.getTimeZone("UTC")
            val timestamp = sdf.format(Date())

            val req = NfcEventRequest(
                nfcUid = nfcUid,
                phoneTimestamp = timestamp,
                location = location
            )
            val resp = api.sendNfcEvent(req)
            if (resp.isSuccessful && resp.body() != null) {
                Result.success(resp.body()!!)
            } else {
                val msg = parseErrorDetail(resp.errorBody()?.string(), "NFC-tapahtuman rekisteröinti epäonnistui")
                Result.failure(Exception(msg))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getNfcEvent(id: Int): Result<NfcEventResponse> {
        return try {
            val resp = api.getNfcEvent(id)
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Tapahtumaa ei löytynyt"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getVideoClip(clipId: Int): Result<VideoClip> {
        return try {
            val resp = api.getVideoClip(clipId)
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Videoleikettä ei löydy"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun approveVideo(clipId: Int): Result<VideoClip> {
        return try {
            val resp = api.approveVideo(clipId)
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Hyväksyntä epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun rejectVideo(clipId: Int): Result<VideoClip> {
        return try {
            val resp = api.rejectVideo(clipId)
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Hylkäys epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getNotes(horseId: Int): Result<List<HorseNote>> {
        return try {
            val resp = api.getHorseNotes(horseId)
            if (resp.isSuccessful) Result.success(resp.body() ?: emptyList())
            else Result.failure(Exception("Muistiinpanojen haku epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun addNote(horseId: Int, content: String): Result<HorseNote> {
        return try {
            val resp = api.addHorseNote(horseId, NoteCreateRequest(content))
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Muistiinpanon tallennus epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getAnalyses(horseId: Int): Result<List<MovementAnalysis>> {
        return try {
            val resp = api.getHorseAnalyses(horseId)
            if (resp.isSuccessful) Result.success(resp.body() ?: emptyList())
            else Result.failure(Exception("Liikeanalyysien haku epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun addAnalysis(req: AnalysisCreateRequest): Result<MovementAnalysis> {
        return try {
            val resp = api.addAnalysis(req)
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Analyysin tallennus epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getWaterMeasurements(limit: Int = 100): Result<List<WaterMeasurement>> {
        return try {
            val resp = api.getWaterMeasurements(limit)
            if (resp.isSuccessful) Result.success(resp.body() ?: emptyList())
            else Result.failure(Exception("Juomamittausten haku epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getWaterDailySummary(days: Int = 14): Result<List<WaterDailySummary>> {
        return try {
            val resp = api.getWaterDailySummary(days)
            if (resp.isSuccessful) Result.success(resp.body() ?: emptyList())
            else Result.failure(Exception("Päiväkohtaisen juomadatan haku epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun syncWater(): Result<SyncResponse> {
        return try {
            val resp = api.syncWater()
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Juomadatan synkronointi epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getStableAir(limit: Int = 40): Result<List<StableAirMeasurement>> {
        return try {
            val resp = api.getStableAir(limit)
            if (resp.isSuccessful) Result.success(resp.body() ?: emptyList())
            else Result.failure(Exception("Talli-ilman mittausten haku epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun syncStableAir(): Result<SyncResponse> {
        return try {
            val resp = api.syncStableAir()
            if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
            else Result.failure(Exception("Ilmanlaatumittausten synkronointi epäonnistui"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun parseWaterTelemetry(rawJson: String?): WaterRawTelemetry? {
        if (rawJson.isNullOrBlank()) return null
        return try {
            gson.fromJson(rawJson, WaterRawTelemetry::class.java)
        } catch (_: Exception) {
            null
        }
    }
}
