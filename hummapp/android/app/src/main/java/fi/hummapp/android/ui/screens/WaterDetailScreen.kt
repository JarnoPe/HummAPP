package fi.hummapp.android.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fi.hummapp.android.data.model.SystemStatus
import fi.hummapp.android.data.model.WaterDailySummary
import fi.hummapp.android.data.model.WaterMeasurement
import fi.hummapp.android.data.repository.HummRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WaterDetailScreen(
    repository: HummRepository
) {
    var measurements by remember { mutableStateOf<List<WaterMeasurement>>(emptyList()) }
    var dailySummaries by remember { mutableStateOf<List<WaterDailySummary>>(emptyList()) }
    var systemStatus by remember { mutableStateOf<SystemStatus?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var isSyncing by remember { mutableStateOf(false) }
    var syncBanner by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun loadWaterData() {
        isLoading = true
        scope.launch {
            try {
                val listDef = async { repository.getWaterMeasurements(100) }
                val dailyDef = async { repository.getWaterDailySummary(14) }
                val statusDef = async { repository.getSystemStatus() }

                listDef.await().onSuccess { measurements = it }
                dailyDef.await().onSuccess { dailySummaries = it }
                statusDef.await().onSuccess { systemStatus = it }
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        loadWaterData()
    }

    val todayStr = remember {
        SimpleDateFormat("yyyy-MM-dd", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(Date())
    }
    val todaySummary = dailySummaries.find { it.date == todayStr }
    val todayLiters = todaySummary?.totalLiters ?: 0.0
    val todayCount = todaySummary?.measurementCount ?: 0
    val latestMeasurement = measurements.firstOrNull()
    val latestTelemetry = repository.parseWaterTelemetry(latestMeasurement?.rawDataJson)
    val avgLiters = if (dailySummaries.isNotEmpty()) {
        dailySummaries.map { it.totalLiters }.average()
    } else 0.0

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = {
                    Column {
                        Text("Juoma-automaatti • Antero", fontWeight = FontWeight.Bold, fontSize = 18.sp, color = Color(0xFF1B325E))
                        Text(
                            text = systemStatus?.waterExternalId ?: "WATER-METER-ANTERO-01",
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Color(0xFF135367)
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { loadWaterData() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Päivitä")
                    }
                }
            )
        }
    ) { padding ->
        if (isLoading && measurements.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Konfiguraatiovaroitus jos Antero puuttuu
                if (systemStatus != null && !systemStatus!!.anteroHorseFound) {
                    item {
                        Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFEF3C7))) {
                            Row(modifier = Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Warning, contentDescription = null, tint = Color(0xFF92400E))
                                Spacer(modifier = Modifier.width(10.dp))
                                Text(
                                    text = "Antero-hevosta ei löydy tietokannasta! Mittauksia ei yhdistetä ennen hevosen luontia.",
                                    fontSize = 12.sp,
                                    color = Color(0xFF92400E)
                                )
                            }
                        }
                    }
                }

                // Pääkortit: Tänään + Viimeisin + Keskiarvo
                item {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFFEFF6FF)),
                            modifier = Modifier.weight(1f)
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("Tänään juotu", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF1E40AF))
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "${String.format(Locale.US, "%.1f", todayLiters)} L",
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Black,
                                    color = Color(0xFF1E3A8A)
                                )
                                Text("$todayCount juomiskertaa", fontSize = 11.sp, color = Color(0xFF3B82F6))
                            }
                        }
                        Card(modifier = Modifier.weight(1f)) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Text("Vuorokausikeskiarvo", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "${String.format(Locale.US, "%.1f", avgLiters)} L",
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Black
                                )
                                Text("${dailySummaries.size} vrk seuranta", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                            }
                        }
                    }
                }

                // Viimeisin juontikerta + telemetriatiedot
                if (latestMeasurement != null) {
                    item {
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
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Icon(Icons.Default.WaterDrop, contentDescription = null, tint = Color(0xFF2563EB))
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text("Viimeisin juomiskerta", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                    }
                                    Text(
                                        text = "${latestMeasurement.liters} L",
                                        fontWeight = FontWeight.Black,
                                        fontSize = 18.sp,
                                        color = Color(0xFF1D4ED8)
                                    )
                                }
                                Text(
                                    text = "Aikaleima: ${latestMeasurement.measuredAt.take(19).replace("T", " ")} UTC",
                                    fontSize = 12.sp
                                )
                                if (latestTelemetry != null) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                                    ) {
                                        TelemetryChip("Virtaus", "${latestTelemetry.flowRateLpm ?: "--"} L/min", Modifier.weight(1f))
                                        TelemetryChip("Kesto", "${latestTelemetry.durationSec ?: "--"} s", Modifier.weight(1f))
                                        TelemetryChip("Veden lämpö", "${latestTelemetry.tempCelsius ?: "--"} °C", Modifier.weight(1f))
                                    }
                                }
                            }
                        }
                    }
                }

                // Päiväkohtainen pylväskuvaaja + synkronointinappi
                item {
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
                                    Text("Päivittäiset juomamäärät", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                    Text("Automaattinen vesimittari (L / vrk)", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                                }
                                Button(
                                    onClick = {
                                        isSyncing = true
                                        syncBanner = null
                                        scope.launch {
                                            repository.syncWater().onSuccess {
                                                syncBanner = "Uusi mittaus synkronoitu Anterolle!"
                                                loadWaterData()
                                            }.onFailure {
                                                syncBanner = it.localizedMessage
                                            }
                                            isSyncing = false
                                        }
                                    },
                                    enabled = !isSyncing,
                                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                ) {
                                    Icon(Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(if (isSyncing) "Haetaan..." else "Hae nyt", fontSize = 12.sp)
                                }
                            }

                            if (syncBanner != null) {
                                Text(syncBanner!!, fontSize = 12.sp, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
                            }

                            if (dailySummaries.isNotEmpty()) {
                                val maxVal = (dailySummaries.maxOfOrNull { it.totalLiters } ?: 45.0).coerceAtLeast(10.0)
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(145.dp)
                                        .padding(top = 8.dp),
                                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                                    verticalAlignment = Alignment.Bottom
                                ) {
                                    dailySummaries.takeLast(10).forEach { day ->
                                        val ratio = (day.totalLiters / maxVal).toFloat().coerceIn(0.08f, 1f)
                                        Column(
                                            modifier = Modifier.weight(1f).fillMaxHeight(),
                                            horizontalAlignment = Alignment.CenterHorizontally,
                                            verticalArrangement = Arrangement.Bottom
                                        ) {
                                            Text(
                                                text = "${day.totalLiters.toInt()}",
                                                fontSize = 9.sp,
                                                fontWeight = FontWeight.Bold
                                            )
                                            Spacer(modifier = Modifier.height(3.dp))
                                            Box(
                                                modifier = Modifier
                                                    .fillMaxWidth(0.75f)
                                                    .fillMaxHeight(ratio * 0.78f)
                                                    .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
                                                    .background(if (day.date == todayStr) Color(0xFF1D4ED8) else Color(0xFF93C5FD))
                                            )
                                            Spacer(modifier = Modifier.height(4.dp))
                                            Text(
                                                text = day.date.takeLast(2),
                                                fontSize = 9.sp,
                                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Yksittäisten juomiskertojen loki
                item {
                    Text(
                        text = "Yksittäiset juomiskerrat (${measurements.size})",
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }

                items(measurements) { m ->
                    val tel = repository.parseWaterTelemetry(m.rawDataJson)
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                    ) {
                        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "${m.liters} litraa",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Black,
                                    color = Color(0xFF1E3A8A)
                                )
                                Surface(
                                    color = if (m.horseId != null) Color(0xFFDBEAFE) else Color(0xFFFEF3C7),
                                    shape = RoundedCornerShape(6.dp)
                                ) {
                                    Text(
                                        text = m.horseName ?: "Tunnistamaton",
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = if (m.horseId != null) Color(0xFF1E40AF) else Color(0xFF92400E),
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                                    )
                                }
                            }
                            Text(
                                text = "${m.measuredAt.take(19).replace("T", " ")} UTC • Laite: ${m.externalWaterId}",
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                            )
                            Text(
                                text = "Mittaus-ID: ${m.externalMeasurementId}",
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                            )
                            if (tel != null) {
                                Text(
                                    text = "Virtaus: ${tel.flowRateLpm ?: "--"} L/min • Kesto: ${tel.durationSec ?: "--"} s • Lämpö: ${tel.tempCelsius ?: "--"} °C",
                                    fontSize = 11.sp,
                                    color = Color(0xFF047857),
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TelemetryChip(label: String, value: String, modifier: Modifier = Modifier) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant,
        shape = RoundedCornerShape(8.dp),
        modifier = modifier
    ) {
        Column(modifier = Modifier.padding(8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(text = label, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
            Text(text = value, fontSize = 13.sp, fontWeight = FontWeight.Bold)
        }
    }
}
