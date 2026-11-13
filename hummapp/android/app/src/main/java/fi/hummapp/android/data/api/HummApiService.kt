package fi.hummapp.android.data.api

import fi.hummapp.android.data.auth.TokenManager
import fi.hummapp.android.data.model.*
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface HummApiService {

    @POST("/api/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @GET("/api/health")
    suspend fun getHealth(): Response<HealthResponse>

    @GET("/api/system/status")
    suspend fun getSystemStatus(): Response<SystemStatus>

    @GET("/api/horses")
    suspend fun getHorses(): Response<List<Horse>>

    @POST("/api/horses")
    suspend fun createHorse(@Body request: HorseCreateRequest): Response<Horse>

    @GET("/api/horses/{id}")
    suspend fun getHorse(@Path("id") id: Int): Response<Horse>

    @PUT("/api/horses/{id}")
    suspend fun updateHorse(
        @Path("id") id: Int,
        @Body request: HorseUpdateRequest
    ): Response<Horse>

    @POST("/api/horses/{id}/nfc-tag")
    suspend fun assignNfcTag(
        @Path("id") id: Int,
        @Body request: AssignNfcTagRequest
    ): Response<NfcTag>

    @GET("/api/nfc-events")
    suspend fun getNfcEvents(@Query("limit") limit: Int = 50): Response<List<NfcEventResponse>>

    @POST("/api/nfc-events")
    suspend fun sendNfcEvent(@Body request: NfcEventRequest): Response<NfcEventResponse>

    @GET("/api/nfc-events/{id}")
    suspend fun getNfcEvent(@Path("id") id: Int): Response<NfcEventResponse>

    @GET("/api/video-clips/{id}")
    suspend fun getVideoClip(@Path("id") id: Int): Response<VideoClip>

    @POST("/api/video-clips/{id}/approve")
    suspend fun approveVideo(@Path("id") id: Int): Response<VideoClip>

    @POST("/api/video-clips/{id}/reject")
    suspend fun rejectVideo(@Path("id") id: Int): Response<VideoClip>

    @GET("/api/horses/{id}/notes")
    suspend fun getHorseNotes(@Path("id") id: Int): Response<List<HorseNote>>

    @POST("/api/horses/{id}/notes")
    suspend fun addHorseNote(
        @Path("id") id: Int,
        @Body request: NoteCreateRequest
    ): Response<HorseNote>

    @GET("/api/horses/{id}/analyses")
    suspend fun getHorseAnalyses(@Path("id") id: Int): Response<List<MovementAnalysis>>

    @POST("/api/analyses")
    suspend fun addAnalysis(@Body request: AnalysisCreateRequest): Response<MovementAnalysis>

    @GET("/api/water")
    suspend fun getWaterMeasurements(@Query("limit") limit: Int = 100): Response<List<WaterMeasurement>>

    @GET("/api/water/daily")
    suspend fun getWaterDailySummary(@Query("days") days: Int = 14): Response<List<WaterDailySummary>>

    @POST("/api/water/sync")
    suspend fun syncWater(): Response<SyncResponse>

    @GET("/api/stable-air")
    suspend fun getStableAir(@Query("limit") limit: Int = 40): Response<List<StableAirMeasurement>>

    @POST("/api/stable-air/sync")
    suspend fun syncStableAir(): Response<SyncResponse>

    companion object {
        fun createOkHttpClient(tokenManager: TokenManager): OkHttpClient {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BASIC
            }

            return OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .addInterceptor { chain ->
                    val original = chain.request()
                    val token = tokenManager.getToken()
                    val requestBuilder = original.newBuilder()
                    if (!token.isNullOrBlank()) {
                        requestBuilder.header("Authorization", "Bearer $token")
                    }
                    chain.proceed(requestBuilder.build())
                }
                .addInterceptor(logging)
                .build()
        }

        fun create(tokenManager: TokenManager): HummApiService {
            val client = createOkHttpClient(tokenManager)
            val baseUrl = tokenManager.getBaseUrl().let {
                if (it.endsWith("/")) it else "$it/"
            }

            return Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(HummApiService::class.java)
        }
    }
}
