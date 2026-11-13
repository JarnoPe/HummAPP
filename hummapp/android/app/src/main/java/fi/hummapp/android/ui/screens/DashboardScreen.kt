package fi.hummapp.android.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fi.hummapp.android.data.auth.TokenManager
import fi.hummapp.android.data.model.*
import fi.hummapp.android.data.repository.HummRepository
import fi.hummapp.android.ui.theme.KaseCrimson
import fi.hummapp.android.ui.theme.KaseGold
import fi.hummapp.android.ui.theme.KaseGreen
import fi.hummapp.android.ui.theme.KaseNavy
import fi.hummapp.android.ui.theme.KasePetrol
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    repository: HummRepository,
    tokenManager: TokenManager,
    onOpenWater: () -> Unit,
    onOpenNfc: () -> Unit,
    onOpenHorses: () -> Unit,
    onLogout: () -> Unit
) {
    var horses by remember { mutableStateOf<List<Horse>>(emptyList()) }
    var waterDaily by remember { mutableStateOf<List<WaterDailySummary>>(emptyList()) }
    var waterList by remember { mutableStateOf<List<WaterMeasurement>>(emptyList()) }
    var airReadings by remember { mutableStateOf<List<StableAirMeasurement>>(emptyList()) }
    var nfcEvents by remember { mutableStateOf<List<NfcEventResponse>>(emptyList()) }
    var systemStatus by remember { mutableStateOf<SystemStatus?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var isSyncingAir by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun loadAll() {
        isLoading = true
        errorMessage = null
        scope.launch {
            try {
                val horsesDef = async { repository.getHorses() }
                val waterDailyDef = async { repository.getWaterDailySummary(7) }
                val waterListDef = async { repository.getWaterMeasurements(20) }
                val airDef = async { repository.getStableAir(20) }
                val eventsDef = async { repository.getNfcEvents(10) }
                val statusDef = async { repository.getSystemStatus() }

                horsesDef.await().onSuccess { horses = it }.onFailure { errorMessage = it.localizedMessage }
                waterDailyDef.await().onSuccess { waterDaily = it }
                waterListDef.await().onSuccess { waterList = it }
                airDef.await().onSuccess { airReadings = it }
                eventsDef.await().onSuccess { nfcEvents = it }
                statusDef.await().onSuccess { systemStatus = it }
            } catch (e: Exception) {
                errorMessage = e.localizedMessage
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        loadAll()
    }

    val todayStr = remember {
        SimpleDateFormat("yyyy-MM-dd", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(Date())
    }
    val todayWaterSummary = waterDaily.find { it.date == todayStr }
    val todayLiters = todayWaterSummary?.totalLiters ?: 0.0
    val todayDrinkCount = todayWaterSummary?.measurementCount ?: 0
    val latestAir = airReadings.firstOrNull()

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = {
                    Column {
                        Text("Katsaus & Mittaukset", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = KaseNavy)
                        Text(
                            text = "${tokenManager.getUsername() ?: "Käyttäjä"} • ${if (systemStatus?.databaseOk == true) "Yhteys OK" else "Yhdistetään..."}",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { loadAll() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Päivitä")
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.Default.ExitToApp, contentDescription = "Kirjaudu ulos")
                    }
                }
            )
        }
    ) { padding ->
        if (isLoading && horses.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                if (errorMessage != null) {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                        Text(
                            text = errorMessage!!,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            fontSize = 12.sp,
                            modifier = Modifier.padding(12.dp)
                        )
                    }
                }

                // Tunnuslukukortit (2x2)
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    MetricSummaryCard(
                        title = "Antero • Juominen",
                        value = "${String.format(Locale.US, "%.1f", todayLiters)} L",
                        subtitle = "$todayDrinkCount krt tänään",
                        accent = KasePetrol,
                        onClick = onOpenWater,
                        modifier = Modifier.weight(1f)
                    )
                    MetricSummaryCard(
                        title = "Talli-ilma",
                        value = if (latestAir?.temperature != null) "${latestAir.temperature} °C" else "--",
                        subtitle = if (latestAir?.humidity != null) "${latestAir.humidity} % kosteus" else "Ei dataa",
                        accent = KaseGreen,
                        onClick = {},
                        modifier = Modifier.weight(1f)
                    )
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    MetricSummaryCard(
                        title = "Hevoset",
                        value = "${horses.size}",
                        subtitle = "Aktiiviset tallihevoset",
                        accent = KaseNavy,
                        onClick = onOpenHorses,
                        modifier = Modifier.weight(1f)
                    )
                    MetricSummaryCard(
                        title = "NFC & Videot",
                        value = "${nfcEvents.size}",
                        subtitle = "Viimeisimmät tapahtumat",
                        accent = KaseCrimson,
                        onClick = onOpenNfc,
                        modifier = Modifier.weight(1f)
                    )
                }

                // Talli-ilman olosuhdemittaukset
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text("Talli-ilman mittaukset", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                Text(
                                    text = latestAir?.location ?: "Päätalli",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                )
                            }
                            FilledTonalButton(
                                onClick = {
                                    isSyncingAir = true
                                    scope.launch {
                                        repository.syncStableAir().onSuccess {
                                            repository.getStableAir(20).onSuccess { airReadings = it }
                                        }
                                        isSyncingAir = false
                                    }
                                },
                                enabled = !isSyncingAir
                            ) {
                                Icon(Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(if (isSyncingAir) "Haetaan..." else "Päivitä", fontSize = 12.sp)
                            }
                        }

                        if (latestAir != null) {
                            AirThresholdBar(
                                label = "Lämpötila",
                                valueText = "${latestAir.temperature ?: "--"} °C",
                                targetText = "Optimi 8–14 °C",
                                progress = (((latestAir.temperature ?: 10.0) - 0.0) / 25.0).toFloat().coerceIn(0f, 1f),
                                barColor = Color(0xFFEA580C)
                            )
                            AirThresholdBar(
                                label = "Ilmankosteus",
                                valueText = "${latestAir.humidity ?: "--"} %",
                                targetText = "Optimi 60–80 %",
                                progress = ((latestAir.humidity ?: 65.0) / 100.0).toFloat().coerceIn(0f, 1f),
                                barColor = Color(0xFF0284C7)
                            )
                            AirThresholdBar(
                                label = "Ammoniakki (NH3)",
                                valueText = "${latestAir.ammonia ?: "--"} ppm",
                                targetText = "Suositus < 10 ppm",
                                progress = ((latestAir.ammonia ?: 2.0) / 12.0).toFloat().coerceIn(0f, 1f),
                                barColor = if ((latestAir.ammonia ?: 0.0) > 10.0) Color(0xFFDC2626) else Color(0xFFD97706)
                            )
                            AirThresholdBar(
                                label = "Hiilidioksidi (CO2)",
                                valueText = "${latestAir.co2?.toInt() ?: "--"} ppm",
                                targetText = "Suositus < 1500 ppm",
                                progress = ((latestAir.co2 ?: 800.0) / 2000.0).toFloat().coerceIn(0f, 1f),
                                barColor = Color(0xFF475569)
                            )
                            AirThresholdBar(
                                label = "Pienhiukkaset (PM2.5)",
                                valueText = "${latestAir.particulateMatter ?: "--"} µg/m³",
                                targetText = "Pölykuorma",
                                progress = ((latestAir.particulateMatter ?: 20.0) / 60.0).toFloat().coerceIn(0f, 1f),
                                barColor = Color(0xFF059669)
                            )
                        } else {
                            Text("Ei ilmanlaatumittauksia saatavilla.", fontSize = 12.sp)
                        }
                    }
                }

                // Anteron 7 päivän juomakehitys
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text("Anteron juomamäärät (7 vrk)", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                                Text("Vain Anterolla juoma-automaatti", fontSize = 11.sp, color = Color(0xFF1D4ED8))
                            }
                            TextButton(onClick = onOpenWater) {
                                Text("Tarkat tiedot →", fontSize = 12.sp)
                            }
                        }

                        if (waterDaily.isNotEmpty()) {
                            val maxLiters = (waterDaily.maxOfOrNull { it.totalLiters } ?: 45.0).coerceAtLeast(10.0)
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(130.dp)
                                    .padding(top = 8.dp),
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalAlignment = Alignment.Bottom
                            ) {
                                waterDaily.forEach { day ->
                                    val ratio = (day.totalLiters / maxLiters).toFloat().coerceIn(0.08f, 1f)
                                    Column(
                                        modifier = Modifier.weight(1f).fillMaxHeight(),
                                        horizontalAlignment = Alignment.CenterHorizontally,
                                        verticalArrangement = Arrangement.Bottom
                                    ) {
                                        Text(
                                            text = "${day.totalLiters.toInt()}L",
                                            fontSize = 10.sp,
                                            fontWeight = FontWeight.Bold
                                        )
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Box(
                                            modifier = Modifier
                                                .fillMaxWidth(0.7f)
                                                .weight(1f, fill = false)
                                                .fillMaxHeight(ratio * 0.78f)
                                                .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
                                                .background(if (day.date == todayStr) Color(0xFF1D4ED8) else Color(0xFF60A5FA))
                                        )
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(
                                            text = day.date.takeLast(5),
                                            fontSize = 9.sp,
                                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                        )
                                    }
                                }
                            }
                        } else {
                            Text("Ei päiväkohtaisia juomamittauksia.", fontSize = 12.sp)
                        }
                    }
                }

                // Viimeisimmät NFC-tapahtumat
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Viimeisimmät NFC & Videot", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                            TextButton(onClick = onOpenNfc) {
                                Text("Avaa leikkuri →", fontSize = 12.sp)
                            }
                        }

                        nfcEvents.take(4).forEach { ev ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column {
                                    Text(
                                        text = ev.horseName ?: "Tuntematon tagi (${ev.nfcUid})",
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 13.sp
                                    )
                                    Text(
                                        text = "#${ev.id} • ${ev.location ?: "kuvausalue-1"} • ${ev.phoneTimestamp.take(16).replace("T", " ")}",
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
                                    )
                                }
                                StatusBadge(status = ev.status)
                            }
                            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MetricSummaryCard(
    title: String,
    value: String,
    subtitle: String,
    accent: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        onClick = onClick,
        modifier = modifier,
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(text = title, fontSize = 11.sp, fontWeight = FontWeight.Bold, color = accent)
            Spacer(modifier = Modifier.height(6.dp))
            Text(text = value, fontSize = 24.sp, fontWeight = FontWeight.Black)
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = subtitle,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }
    }
}

@Composable
private fun AirThresholdBar(
    label: String,
    valueText: String,
    targetText: String,
    progress: Float,
    barColor: Color
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(text = "$label: $valueText", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
            Text(
                text = targetText,
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }
        LinearProgressIndicator(
            progress = { progress },
            color = barColor,
            trackColor = barColor.copy(alpha = 0.15f),
            modifier = Modifier
                .fillMaxWidth()
                .height(7.dp)
                .clip(RoundedCornerShape(4.dp))
        )
    }
}

@Composable
fun StatusBadge(status: String) {
    val (bg, fg) = when (status) {
        "APPROVED" -> Color(0xFFD1FAE5) to Color(0xFF065F46)
        "READY" -> Color(0xFFDBEAFE) to Color(0xFF1E40AF)
        "PROCESSING", "WAITING_FOR_RECORDING", "RECEIVED" -> Color(0xFFFEF3C7) to Color(0xFF92400E)
        "REJECTED" -> Color(0xFFE2E8F0) to Color(0xFF475569)
        else -> Color(0xFFFEE2E2) to Color(0xFF991B1B)
    }
    Surface(color = bg, shape = RoundedCornerShape(6.dp)) {
        Text(
            text = status,
            color = fg,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
        )
    }
}
