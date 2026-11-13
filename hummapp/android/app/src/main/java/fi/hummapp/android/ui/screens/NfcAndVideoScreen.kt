package fi.hummapp.android.ui.screens

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fi.hummapp.android.data.model.NfcEventResponse
import fi.hummapp.android.data.repository.HummRepository
import fi.hummapp.android.nfc.NfcManager
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NfcAndVideoScreen(
    nfcManager: NfcManager,
    repository: HummRepository,
    lastScannedUid: String?,
    onClearScannedUid: () -> Unit,
    onOpenVideo: (Int) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var locationInput by remember { mutableStateOf("kuvausalue-1") }
    var isSending by remember { mutableStateOf(false) }
    var activeEvent by remember { mutableStateOf<NfcEventResponse?>(null) }
    var eventsList by remember { mutableStateOf<List<NfcEventResponse>>(emptyList()) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isPollingVideo by remember { mutableStateOf(false) }

    val nfcSupported = nfcManager.isNfcSupported()
    val nfcEnabled = nfcManager.isNfcEnabled()

    fun refreshEvents() {
        scope.launch {
            repository.getNfcEvents(40).onSuccess {
                eventsList = it
            }
        }
    }

    fun triggerNfcScan(uid: String) {
        isSending = true
        errorMessage = null
        activeEvent = null

        scope.launch {
            val res = repository.sendNfcEvent(uid, locationInput.ifBlank { "kuvausalue-1" })
            isSending = false
            res.onSuccess { event ->
                activeEvent = event
                refreshEvents()
                if (event.status != "FAILED" && event.status != "READY" && event.status != "APPROVED") {
                    isPollingVideo = true
                }
            }.onFailure { err ->
                errorMessage = err.localizedMessage ?: "Virhe NFC-tapahtuman lähetyksessä"
                refreshEvents()
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshEvents()
    }

    // Fyysinen NFC-luku
    LaunchedEffect(lastScannedUid) {
        if (!lastScannedUid.isNullOrBlank()) {
            val uid = lastScannedUid
            onClearScannedUid()
            triggerNfcScan(uid)
        }
    }

    // Taustapollauksen seuranta leikkauksen valmistumiselle
    LaunchedEffect(isPollingVideo, activeEvent?.id) {
        val eventId = activeEvent?.id
        if (isPollingVideo && eventId != null) {
            var attempts = 0
            while (attempts < 25 && isPollingVideo) {
                delay(2000)
                repository.getNfcEvent(eventId).onSuccess { updated ->
                    activeEvent = updated
                    if (updated.status == "READY" || updated.status == "FAILED" || updated.status == "APPROVED") {
                        isPollingVideo = false
                        refreshEvents()
                    }
                }
                attempts++
            }
            isPollingVideo = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = { Text("NFC & Videoleikkuri", fontWeight = FontWeight.Bold, color = androidx.compose.ui.graphics.Color(0xFF1B325E)) },
                actions = {
                    IconButton(onClick = { refreshEvents() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Päivitä lista")
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // 1. NFC-lukijan tila ja testisimulaattori
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(48.dp)
                                    .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    Icons.Default.Nfc,
                                    contentDescription = "NFC",
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(28.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(12.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text("NFC-riimulukija valmiina", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                Text(
                                    text = when {
                                        !nfcSupported -> "Laitteessa ei ole NFC-sirua (voit testata alta)."
                                        !nfcEnabled -> "NFC on pois päältä laitteen asetuksista."
                                        else -> "Vie puhelin riimutagiin leikataksesi 50s videon."
                                    },
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                                )
                            }
                        }

                        if (nfcSupported && !nfcEnabled) {
                            Button(
                                onClick = { context.startActivity(Intent(Settings.ACTION_NFC_SETTINGS)) },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Ota NFC käyttöön asetuksista")
                            }
                        }

                        OutlinedTextField(
                            value = locationInput,
                            onValueChange = { locationInput = it },
                            label = { Text("Kuvauspaikka") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )

                        // Pikatestausnapit ilman fyysistä tagia
                        Text(
                            text = "Pikatesti (lähettää NFC-tapahtuman palvelimelle):",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            FilledTonalButton(
                                onClick = { triggerNfcScan("04A31B92C56F80") },
                                enabled = !isSending,
                                modifier = Modifier.weight(1f),
                                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 6.dp)
                            ) {
                                Text("Antero", fontSize = 11.sp)
                            }
                            FilledTonalButton(
                                onClick = { triggerNfcScan("04E24589F10123") },
                                enabled = !isSending,
                                modifier = Modifier.weight(1f),
                                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 6.dp)
                            ) {
                                Text("Valo", fontSize = 11.sp)
                            }
                            OutlinedButton(
                                onClick = { triggerNfcScan("DEADBEEF9999") },
                                enabled = !isSending,
                                modifier = Modifier.weight(1f),
                                contentPadding = PaddingValues(horizontal = 6.dp, vertical = 6.dp)
                            ) {
                                Text("Tuntematon", fontSize = 11.sp)
                            }
                        }
                    }
                }
            }

            if (isSending) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(10.dp))
                        Text("Lähetetään NFC-tapahtumaa...", fontSize = 13.sp)
                    }
                }
            }

            if (errorMessage != null) {
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                        Text(
                            text = errorMessage!!,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            fontSize = 12.sp,
                            modifier = Modifier.padding(14.dp)
                        )
                    }
                }
            }

            // 2. Käynnissä oleva / viimeisin NFC-leikkaus
            if (activeEvent != null) {
                val ev = activeEvent!!
                item {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Tunnistettu: ${ev.horseName ?: "Tuntematon"}",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp
                                )
                                StatusBadge(status = ev.status)
                            }
                            Text(
                                text = "Tapahtuma #${ev.id} • Tag UID: ${ev.nfcUid}",
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace
                            )
                            if (isPollingVideo) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("FFmpeg leikkaa videota (10s ennen + 40s jälkeen)...", fontSize = 12.sp)
                                }
                            }
                            val clipId = ev.videoClipId
                            if (clipId != null && (ev.status == "READY" || ev.status == "APPROVED")) {
                                Button(
                                    onClick = { onOpenVideo(clipId) },
                                    modifier = Modifier.fillMaxWidth().padding(top = 6.dp)
                                ) {
                                    Icon(Icons.Default.PlayArrow, contentDescription = null)
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Katso leikattu video (#$clipId)")
                                }
                            }
                        }
                    }
                }
            }

            // 3. Videoleikkeiden ja NFC-tapahtumien lista
            item {
                Text(
                    text = "Videoleikkeet ja tapahtumat (${eventsList.size})",
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    modifier = Modifier.padding(top = 6.dp)
                )
            }

            items(eventsList) { ev ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = ev.horseName ?: "Tuntematon tagi",
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 15.sp
                                )
                                Text(
                                    text = "#${ev.id} • ${ev.nfcUid} • ${ev.location ?: "kuvausalue-1"}",
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                )
                            }
                            StatusBadge(status = ev.status)
                        }

                        Text(
                            text = "Aika: ${ev.phoneTimestamp.take(19).replace("T", " ")} UTC",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                        )

                        if (!ev.errorMessage.isNullOrBlank()) {
                            Text(
                                text = ev.errorMessage,
                                fontSize = 11.sp,
                                color = MaterialTheme.colorScheme.error
                            )
                        }

                        val clipId = ev.videoClipId
                        if (clipId != null) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Button(
                                    onClick = { onOpenVideo(clipId) },
                                    modifier = Modifier.weight(1f),
                                    contentPadding = PaddingValues(vertical = 8.dp)
                                ) {
                                    Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("Katso", fontSize = 12.sp)
                                }
                                if (ev.status != "APPROVED") {
                                    FilledTonalButton(
                                        onClick = {
                                            scope.launch {
                                                repository.approveVideo(clipId).onSuccess { refreshEvents() }
                                            }
                                        },
                                        modifier = Modifier.weight(1f),
                                        contentPadding = PaddingValues(vertical = 8.dp)
                                    ) {
                                        Text("Hyväksy", fontSize = 12.sp)
                                    }
                                }
                                if (ev.status != "REJECTED") {
                                    OutlinedButton(
                                        onClick = {
                                            scope.launch {
                                                repository.rejectVideo(clipId).onSuccess { refreshEvents() }
                                            }
                                        },
                                        modifier = Modifier.weight(1f),
                                        contentPadding = PaddingValues(vertical = 8.dp)
                                    ) {
                                        Text("Hylkää", fontSize = 12.sp)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
