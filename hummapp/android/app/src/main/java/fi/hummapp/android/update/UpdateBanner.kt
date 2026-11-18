package fi.hummapp.android.update

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SystemUpdate
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.repeatOnLifecycle
import fi.hummapp.android.ui.theme.KaseNavy
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File

private const val CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000L

private sealed interface UpdateStep {
    data object Offer : UpdateStep
    data class Downloading(val progress: Float) : UpdateStep
    data object NeedsPermission : UpdateStep
    data object Failed : UpdateStep
}

/**
 * Ilmoitus uudesta sovellusversiosta ja Päivitä-painike.
 * Tarkistaa päivitykset, kun sovellus tulee näkyviin, ja sen jälkeen kuuden tunnin välein.
 */
@Composable
fun UpdateBanner(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()

    var update by remember { mutableStateOf<AppUpdate?>(null) }
    var dismissedCode by rememberSaveable { mutableIntStateOf(0) }
    var step by remember { mutableStateOf<UpdateStep>(UpdateStep.Offer) }
    var downloaded by remember { mutableStateOf<File?>(null) }

    LaunchedEffect(lifecycleOwner) {
        lifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                AppUpdater.checkForUpdate()?.let { found ->
                    if (found.versionCode != update?.versionCode) {
                        update = found
                        downloaded = null
                        step = UpdateStep.Offer
                    }
                }
                delay(CHECK_INTERVAL_MS)
            }
        }
    }

    val current = update ?: return
    if (current.versionCode == dismissedCode) return

    fun installOrAskPermission(apk: File) {
        if (AppUpdater.canInstall(context)) {
            step = UpdateStep.Offer
            AppUpdater.install(context, apk)
        } else {
            step = UpdateStep.NeedsPermission
            AppUpdater.openInstallPermissionSettings(context)
        }
    }

    fun startUpdate() {
        downloaded?.takeIf { it.exists() }?.let { installOrAskPermission(it); return }
        step = UpdateStep.Downloading(0f)
        scope.launch {
            runCatching {
                AppUpdater.download(context, current) { p -> step = UpdateStep.Downloading(p) }
            }.onSuccess { apk ->
                downloaded = apk
                installOrAskPermission(apk)
            }.onFailure {
                step = UpdateStep.Failed
            }
        }
    }

    Surface(
        color = Color(0xFFE8F3EC),
        modifier = modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Default.SystemUpdate,
                    contentDescription = null,
                    tint = Color(0xFF1F6B44),
                    modifier = Modifier.size(20.dp)
                )
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text(
                        text = "Uusi versio ${current.versionName} on saatavilla",
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp,
                        color = KaseNavy
                    )
                    val detail = when (val s = step) {
                        UpdateStep.Offer -> "Käytössä on versio ${AppUpdater.currentVersionName}."
                        is UpdateStep.Downloading -> "Ladataan päivitystä… ${(s.progress * 100).toInt()} %"
                        UpdateStep.NeedsPermission ->
                            "Salli asennus HummAPPille avautuneessa asetuksessa ja paina sitten Päivitä uudelleen."
                        UpdateStep.Failed -> "Lataus epäonnistui. Tarkista nettiyhteys ja yritä uudelleen."
                    }
                    Text(text = detail, fontSize = 12.sp, color = Color(0xFF4A4B4D))
                }
            }

            val s = step
            if (s is UpdateStep.Downloading) {
                Spacer(Modifier.height(8.dp))
                LinearProgressIndicator(
                    progress = { s.progress },
                    color = Color(0xFF1F6B44),
                    modifier = Modifier.fillMaxWidth()
                )
            } else {
                Row(
                    horizontalArrangement = Arrangement.End,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    TextButton(onClick = { dismissedCode = current.versionCode }) {
                        Text("Myöhemmin")
                    }
                    Spacer(Modifier.width(4.dp))
                    Button(
                        onClick = { startUpdate() },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1F6B44))
                    ) {
                        Text("Päivitä")
                    }
                }
            }
        }
    }
}
