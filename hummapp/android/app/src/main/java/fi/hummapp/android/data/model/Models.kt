package fi.hummapp.android.data.model

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val username: String,
    val password: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    val role: String,
    val username: String,
    @SerializedName("user_id") val userId: Int
)

data class HealthResponse(
    val status: String,
    val app: String?,
    val database: String?,
    val timestamp: String?
)

data class SystemStatus(
    val status: String,
    @SerializedName("app_name") val appName: String,
    val version: String,
    @SerializedName("database_ok") val databaseOk: Boolean,
    @SerializedName("camera_dir_exists") val cameraDirExists: Boolean,
    @SerializedName("video_dir_exists") val videoDirExists: Boolean,
    @SerializedName("antero_configured") val anteroConfigured: Boolean,
    @SerializedName("antero_horse_found") val anteroHorseFound: Boolean,
    @SerializedName("antero_horse_id") val anteroHorseId: Int?,
    @SerializedName("water_external_id") val waterExternalId: String,
    @SerializedName("mock_water_enabled") val mockWaterEnabled: Boolean,
    @SerializedName("mock_air_enabled") val mockAirEnabled: Boolean,
    @SerializedName("uptime_utc") val uptimeUtc: String
)

data class NfcTag(
    val id: Int,
    @SerializedName("horse_id") val horseId: Int,
    @SerializedName("nfc_uid") val nfcUid: String,
    val active: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class Horse(
    val id: Int,
    val name: String,
    val breed: String? = null,
    @SerializedName("birth_year") val birthYear: Int? = null,
    @SerializedName("owner_name") val ownerName: String? = null,
    @SerializedName("stall_box") val stallBox: String? = null,
    val description: String? = null,
    val active: Boolean,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("nfc_tags") val nfcTags: List<NfcTag>? = null
)

data class HorseCreateRequest(
    val name: String,
    val breed: String? = null,
    @SerializedName("birth_year") val birthYear: Int? = null,
    @SerializedName("owner_name") val ownerName: String? = null,
    @SerializedName("stall_box") val stallBox: String? = null,
    val description: String? = null
)

data class HorseUpdateRequest(
    val name: String? = null,
    val breed: String? = null,
    @SerializedName("birth_year") val birthYear: Int? = null,
    @SerializedName("owner_name") val ownerName: String? = null,
    @SerializedName("stall_box") val stallBox: String? = null,
    val description: String? = null
)

data class AssignNfcTagRequest(
    @SerializedName("nfc_uid") val nfcUid: String
)

data class NfcEventRequest(
    @SerializedName("nfc_uid") val nfcUid: String,
    @SerializedName("phone_timestamp") val phoneTimestamp: String,
    val location: String = "kuvausalue-1"
)

data class NfcEventResponse(
    val id: Int,
    @SerializedName("horse_id") val horseId: Int?,
    @SerializedName("horse_name") val horseName: String?,
    @SerializedName("nfc_uid") val nfcUid: String,
    @SerializedName("phone_timestamp") val phoneTimestamp: String,
    @SerializedName("server_timestamp") val serverTimestamp: String,
    @SerializedName("user_id") val userId: Int?,
    val location: String?,
    val status: String,
    @SerializedName("error_message") val errorMessage: String?,
    @SerializedName("video_clip_id") val videoClipId: Int? = null,
    @SerializedName("video_clip_status") val videoClipStatus: String? = null
)

data class VideoClip(
    val id: Int,
    @SerializedName("nfc_event_id") val nfcEventId: Int,
    @SerializedName("relative_file_path") val relativeFilePath: String,
    val status: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("approved_at") val approvedAt: String?,
    @SerializedName("rejected_at") val rejectedAt: String?
)

data class HorseNote(
    val id: Int,
    @SerializedName("horse_id") val horseId: Int,
    val content: String,
    @SerializedName("user_id") val userId: Int?,
    @SerializedName("author_username") val authorUsername: String?,
    @SerializedName("created_at") val createdAt: String
)

data class NoteCreateRequest(
    val content: String
)

data class MovementAnalysis(
    val id: Int,
    @SerializedName("horse_id") val horseId: Int,
    @SerializedName("video_clip_id") val videoClipId: Int?,
    @SerializedName("analysis_method") val analysisMethod: String,
    @SerializedName("analysis_timestamp") val analysisTimestamp: String,
    val summary: String,
    @SerializedName("result_json") val resultJson: String?,
    val status: String,
    @SerializedName("created_by") val createdBy: Int?,
    @SerializedName("created_at") val createdAt: String
)

data class AnalysisCreateRequest(
    @SerializedName("horse_id") val horseId: Int,
    @SerializedName("video_clip_id") val videoClipId: Int? = null,
    @SerializedName("analysis_method") val analysisMethod: String,
    val summary: String,
    @SerializedName("result_json") val resultJson: String? = null,
    val status: String = "APPROVED"
)

data class WaterMeasurement(
    val id: Int,
    @SerializedName("horse_id") val horseId: Int?,
    @SerializedName("horse_name") val horseName: String?,
    @SerializedName("external_measurement_id") val externalMeasurementId: String,
    @SerializedName("external_water_id") val externalWaterId: String,
    @SerializedName("measured_at") val measuredAt: String,
    val liters: Double,
    @SerializedName("raw_data_json") val rawDataJson: String?,
    @SerializedName("created_at") val createdAt: String
)

data class WaterRawTelemetry(
    val source: String? = null,
    @SerializedName("device_serial") val deviceSerial: String? = null,
    @SerializedName("flow_rate_lpm") val flowRateLpm: Double? = null,
    @SerializedName("duration_sec") val durationSec: Int? = null,
    @SerializedName("temp_celsius") val tempCelsius: Double? = null
)

data class WaterDailySummary(
    val date: String,
    @SerializedName("total_liters") val totalLiters: Double,
    @SerializedName("measurement_count") val measurementCount: Int
)

data class StableAirMeasurement(
    val id: Int,
    @SerializedName("sensor_id") val sensorId: String,
    val location: String?,
    @SerializedName("measured_at") val measuredAt: String,
    val temperature: Double?,
    val humidity: Double?,
    val ammonia: Double?,
    val co2: Double?,
    @SerializedName("particulate_matter") val particulateMatter: Double?,
    @SerializedName("raw_data_json") val rawDataJson: String?,
    @SerializedName("created_at") val createdAt: String
)

data class SyncResponse(
    val message: String,
    @SerializedName("new_records") val newRecords: Int
)
