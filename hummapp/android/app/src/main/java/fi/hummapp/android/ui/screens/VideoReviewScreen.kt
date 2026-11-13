package fi.hummapp.android.ui.screens

import android.content.Intent
import android.net.Uri
import android.view.ViewGroup
import android.widget.FrameLayout
import androidx.annotation.OptIn
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.ui.PlayerView
import fi.hummapp.android.data.api.HummApiService
import fi.hummapp.android.data.auth.TokenManager
import fi.hummapp.android.data.model.VideoClip
import fi.hummapp.android.data.repository.HummRepository
import kotlinx.coroutines.launch

@OptIn(UnstableApi::class)
@kotlin.OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VideoReviewScreen(
    clipId: Int,
    repository: HummRepository,
    tokenManager: TokenManager,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var clipInfo by remember { mutableStateOf<VideoClip?>(null) }
    var statusText by remember { mutableStateOf("READY") }
    var isProcessing by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }

    val videoUrl = "${tokenManager.getBaseUrl()}/api/video-clips/$clipId/download"
    val token = tokenManager.getToken() ?: ""

    // Haetaan leikkeen metatiedot
    LaunchedEffect(clipId) {
        repository.getVideoClip(clipId).onSuccess { clip ->
            clipInfo = clip
            statusText = clip.status
        }
    }

    // Autentikoitu ExoPlayer OkHttp-asiakkaalla (välittää Authorization: Bearer <token>)
    val exoPlayer = remember(clipId) {
        val okHttpClient = HummApiService.createOkHttpClient(tokenManager)
        val dataSourceFactory = OkHttpDataSource.Factory(okHttpClient)
        ExoPlayer.Builder(context)
            .setMediaSourceFactory(DefaultMediaSourceFactory(dataSourceFactory))
            .build()
            .apply {
                setMediaItem(MediaItem.fromUri(videoUrl))
                prepare()
                playWhenReady = true
            }
    }

    DisposableEffect(Unit) {
        onDispose {
            exoPlayer.release()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = { Text("Videoleikkeen tarkastus") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Takaisin")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Sisäänrakennettu MP4-videosoitin
            Card(modifier = Modifier.fillMaxWidth()) {
                AndroidView(
                    factory = { ctx ->
                        PlayerView(ctx).apply {
                            player = exoPlayer
                            layoutParams = FrameLayout.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT,
                                ViewGroup.LayoutParams.MATCH_PARENT
                            )
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(16f / 9f)
                )
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = "Videoleike #$clipId", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        StatusBadge(status = statusText)
                    }
                    if (clipInfo != null) {
                        Text(
                            text = "Tapahtuma #${clipInfo!!.nfcEventId} • ${clipInfo!!.relativeFilePath}",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                        )
                    }
                }
            }

            if (message != null) {
                Text(
                    text = message!!,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Button(
                    onClick = {
                        isProcessing = true
                        scope.launch {
                            repository.approveVideo(clipId).onSuccess {
                                statusText = "APPROVED"
                                message = "Videointikerta hyväksytty (APPROVED)!"
                                isProcessing = false
                            }.onFailure {
                                message = "Hyväksyminen epäonnistui."
                                isProcessing = false
                            }
                        }
                    },
                    modifier = Modifier.weight(1f),
                    enabled = !isProcessing && statusText != "APPROVED"
                ) {
                    Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Hyväksy")
                }

                OutlinedButton(
                    onClick = {
                        isProcessing = true
                        scope.launch {
                            repository.rejectVideo(clipId).onSuccess {
                                statusText = "REJECTED"
                                message = "Videointikerta hylätty (REJECTED)."
                                isProcessing = false
                            }.onFailure {
                                message = "Hylkääminen epäonnistui."
                                isProcessing = false
                            }
                        }
                    },
                    modifier = Modifier.weight(1f),
                    enabled = !isProcessing && statusText != "REJECTED"
                ) {
                    Icon(Icons.Default.Close, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Hylkää")
                }
            }

            TextButton(
                onClick = {
                    val downloadUri = Uri.parse("$videoUrl?token=$token")
                    val intent = Intent(Intent.ACTION_VIEW, downloadUri)
                    context.startActivity(intent)
                }
            ) {
                Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("Lataa tai avaa ulkoisessa soittimessa", fontSize = 12.sp)
            }
        }
    }
}
