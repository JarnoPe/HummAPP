package fi.hummapp.android.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fi.hummapp.android.data.auth.TokenManager
import fi.hummapp.android.data.model.Horse
import fi.hummapp.android.data.repository.HummRepository
import fi.hummapp.android.ui.theme.KaseCrimson
import fi.hummapp.android.ui.theme.KaseNavy
import fi.hummapp.android.ui.theme.KasePetrol
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HorseListScreen(
    repository: HummRepository,
    tokenManager: TokenManager,
    onHorseClick: (Int) -> Unit,
    onNfcClick: () -> Unit,
    onLogout: () -> Unit
) {
    var horses by remember { mutableStateOf<List<Horse>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var showAddDialog by remember { mutableStateOf(false) }

    var newHorseName by remember { mutableStateOf("") }
    var newBreed by remember { mutableStateOf("") }
    var newBirthYear by remember { mutableStateOf("") }
    var newOwner by remember { mutableStateOf("") }
    var newStallBox by remember { mutableStateOf("") }
    var newDescription by remember { mutableStateOf("") }
    var dialogError by remember { mutableStateOf<String?>(null) }

    var tagHorseTarget by remember { mutableStateOf<Horse?>(null) }
    var newTagUid by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()

    fun loadHorses() {
        isLoading = true
        errorMessage = null
        scope.launch {
            repository.getHorses()
                .onSuccess {
                    horses = it
                    isLoading = false
                }
                .onFailure {
                    errorMessage = it.localizedMessage ?: "Virhe hevosten haussa."
                    isLoading = false
                }
        }
    }

    LaunchedEffect(Unit) {
        loadHorses()
    }

    if (showAddDialog) {
        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            title = { Text("Lisää uusi hevonen", fontWeight = FontWeight.Bold, color = KaseNavy) },
            text = {
                Column(
                    modifier = Modifier.verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (dialogError != null) {
                        Text(dialogError!!, color = MaterialTheme.colorScheme.error, fontSize = 12.sp)
                    }
                    OutlinedTextField(
                        value = newHorseName,
                        onValueChange = { newHorseName = it },
                        label = { Text("Hevosen nimi *") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newBreed,
                        onValueChange = { newBreed = it },
                        label = { Text("Rotu (esim. Suomenhevonen)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = newBirthYear,
                            onValueChange = { newBirthYear = it.filter { ch -> ch.isDigit() }.take(4) },
                            label = { Text("Syntymävuosi") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                        OutlinedTextField(
                            value = newStallBox,
                            onValueChange = { newStallBox = it },
                            label = { Text("Karsina") },
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    OutlinedTextField(
                        value = newOwner,
                        onValueChange = { newOwner = it },
                        label = { Text("Omistaja / Talli") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = newDescription,
                        onValueChange = { newDescription = it },
                        label = { Text("Kuvaus / lisätiedot") },
                        maxLines = 3,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newHorseName.isNotBlank()) {
                            dialogError = null
                            scope.launch {
                                repository.createHorse(
                                    name = newHorseName.trim(),
                                    breed = newBreed.trim().ifBlank { null },
                                    birthYear = newBirthYear.toIntOrNull(),
                                    ownerName = newOwner.trim().ifBlank { null },
                                    stallBox = newStallBox.trim().ifBlank { null },
                                    description = newDescription.trim().ifBlank { null }
                                ).onSuccess {
                                    newHorseName = ""
                                    newBreed = ""
                                    newBirthYear = ""
                                    newOwner = ""
                                    newStallBox = ""
                                    newDescription = ""
                                    showAddDialog = false
                                    loadHorses()
                                }.onFailure { err ->
                                    dialogError = err.localizedMessage ?: "Tallennus epäonnistui"
                                }
                            }
                        }
                    }
                ) { Text("Tallenna") }
            },
            dismissButton = {
                TextButton(onClick = { showAddDialog = false }) { Text("Peruuta") }
            }
        )
    }

    if (tagHorseTarget != null) {
        AlertDialog(
            onDismissRequest = { tagHorseTarget = null },
            title = { Text("Yhdistä NFC-tagi: ${tagHorseTarget!!.name}") },
            text = {
                OutlinedTextField(
                    value = newTagUid,
                    onValueChange = { newTagUid = it },
                    label = { Text("NFC UID (heksa)") },
                    placeholder = { Text("04A31B92C56F80") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newTagUid.isNotBlank()) {
                            scope.launch {
                                repository.assignNfcTag(tagHorseTarget!!.id, newTagUid.trim()).onSuccess {
                                    newTagUid = ""
                                    tagHorseTarget = null
                                    loadHorses()
                                }
                            }
                        }
                    }
                ) { Text("Yhdistä") }
            },
            dismissButton = {
                TextButton(onClick = { tagHorseTarget = null }) { Text("Peruuta") }
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = {
                    Column {
                        Text("Tallin hevoset", fontWeight = FontWeight.Bold, color = KaseNavy)
                        Text(
                            text = "Avaa hevonen muokataksesi tietoja ja muistiinpanoja",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { showAddDialog = true }) {
                        Icon(Icons.Default.Add, contentDescription = "Lisää hevonen", tint = KaseCrimson)
                    }
                    IconButton(onClick = { loadHorses() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Päivitä")
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.Default.ExitToApp, contentDescription = "Kirjaudu ulos")
                    }
                }
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onNfcClick,
                containerColor = KaseNavy,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                icon = { Icon(Icons.Default.Nfc, contentDescription = null) },
                text = { Text("NFC-luku") }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when {
                isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                errorMessage != null -> {
                    Column(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(text = errorMessage!!, color = MaterialTheme.colorScheme.error)
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(onClick = { loadHorses() }) {
                            Text("Yritä uudelleen")
                        }
                    }
                }
                horses.isEmpty() -> {
                    Text(
                        text = "Ei hevosia tallennettuna palvelimelle.",
                        modifier = Modifier.align(Alignment.Center),
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                    )
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 84.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        items(horses) { horse ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { onHorseClick(horse.id) },
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(16.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                        Text(
                                            text = horse.name,
                                            fontSize = 18.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = KaseNavy
                                        )
                                        val metaParts = listOfNotNull(
                                            horse.breed?.takeIf { it.isNotBlank() },
                                            horse.birthYear?.let { "s. $it" },
                                            horse.stallBox?.takeIf { it.isNotBlank() }
                                        )
                                        if (metaParts.isNotEmpty()) {
                                            Text(
                                                text = metaParts.joinToString(" • "),
                                                fontSize = 12.sp,
                                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.78f)
                                            )
                                        }
                                        if (!horse.ownerName.isNullOrBlank()) {
                                            Text(
                                                text = "Omistaja: ${horse.ownerName}",
                                                fontSize = 11.sp,
                                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                            )
                                        }
                                        if (horse.name.equals("Antero", ignoreCase = true)) {
                                            Text(
                                                text = "Juoma-automaatti aktiivinen",
                                                fontSize = 11.sp,
                                                color = KasePetrol,
                                                fontWeight = FontWeight.SemiBold
                                            )
                                        }
                                        val tags = horse.nfcTags.orEmpty()
                                        if (tags.isNotEmpty()) {
                                            Text(
                                                text = "NFC: ${tags.joinToString { it.nfcUid }}",
                                                fontSize = 11.sp,
                                                fontFamily = FontFamily.Monospace,
                                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                                            )
                                        } else {
                                            Text(
                                                text = "Ei yhdistettyä NFC-tagia",
                                                fontSize = 11.sp,
                                                color = MaterialTheme.colorScheme.error
                                            )
                                        }
                                    }
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        IconButton(onClick = { tagHorseTarget = horse }) {
                                            Icon(Icons.Default.Nfc, contentDescription = "Yhdistä tagi", tint = KaseNavy)
                                        }
                                        Icon(
                                            Icons.Default.ChevronRight,
                                            contentDescription = "Avaa ja muokkaa",
                                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
                                        )
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
