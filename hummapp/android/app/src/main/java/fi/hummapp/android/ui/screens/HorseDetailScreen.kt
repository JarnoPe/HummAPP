package fi.hummapp.android.ui.screens

import androidx.compose.foundation.layout.*
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
import fi.hummapp.android.data.model.Horse
import fi.hummapp.android.data.model.HorseNote
import fi.hummapp.android.data.model.HorseUpdateRequest
import fi.hummapp.android.data.repository.HummRepository
import fi.hummapp.android.ui.theme.KaseCrimson
import fi.hummapp.android.ui.theme.KaseGreen
import fi.hummapp.android.ui.theme.KaseNavy
import fi.hummapp.android.ui.theme.KasePetrol
import kotlinx.coroutines.async
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HorseDetailScreen(
    horseId: Int,
    repository: HummRepository,
    onBack: () -> Unit,
    onOpenNotes: () -> Unit,
    onOpenAnalysis: () -> Unit
) {
    var horse by remember { mutableStateOf<Horse?>(null) }
    var notes by remember { mutableStateOf<List<HorseNote>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var feedbackMessage by remember { mutableStateOf<String?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Pikalisäys muistiinpanolle suoraan hevoskortilta
    var quickNoteContent by remember { mutableStateOf("") }
    var isSavingNote by remember { mutableStateOf(false) }

    // Muokkausdialogi hevosen tiedoille
    var showEditDialog by remember { mutableStateOf(false) }
    var editName by remember { mutableStateOf("") }
    var editBreed by remember { mutableStateOf("") }
    var editBirthYear by remember { mutableStateOf("") }
    var editOwner by remember { mutableStateOf("") }
    var editStallBox by remember { mutableStateOf("") }
    var editDescription by remember { mutableStateOf("") }
    var isSavingHorse by remember { mutableStateOf(false) }

    // NFC-tagin yhdistysdialogi
    var showTagDialog by remember { mutableStateOf(false) }
    var newTagUid by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    fun loadData() {
        isLoading = true
        scope.launch {
            val hDef = async { repository.getHorses() }
            val nDef = async { repository.getNotes(horseId) }
            hDef.await().onSuccess { list ->
                horse = list.find { it.id == horseId }
            }.onFailure { err ->
                errorMessage = err.localizedMessage
            }
            nDef.await().onSuccess { notes = it }
            isLoading = false
        }
    }

    LaunchedEffect(horseId) {
        loadData()
    }

    if (showEditDialog && horse != null) {
        AlertDialog(
            onDismissRequest = { if (!isSavingHorse) showEditDialog = false },
            title = { Text("Muokkaa hevosen tietoja", fontWeight = FontWeight.Bold, color = KaseNavy) },
            text = {
                Column(
                    modifier = Modifier.verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = editName,
                        onValueChange = { editName = it },
                        label = { Text("Hevosen nimi *") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = editBreed,
                        onValueChange = { editBreed = it },
                        label = { Text("Rotu") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = editBirthYear,
                            onValueChange = { editBirthYear = it.filter { ch -> ch.isDigit() }.take(4) },
                            label = { Text("Syntymävuosi") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                        OutlinedTextField(
                            value = editStallBox,
                            onValueChange = { editStallBox = it },
                            label = { Text("Karsina") },
                            singleLine = true,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    OutlinedTextField(
                        value = editOwner,
                        onValueChange = { editOwner = it },
                        label = { Text("Omistaja / Talli") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = editDescription,
                        onValueChange = { editDescription = it },
                        label = { Text("Kuvaus / lisätiedot") },
                        maxLines = 4,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    enabled = !isSavingHorse && editName.isNotBlank(),
                    onClick = {
                        isSavingHorse = true
                        errorMessage = null
                        feedbackMessage = null
                        scope.launch {
                            val req = HorseUpdateRequest(
                                name = editName.trim(),
                                breed = editBreed.trim().ifBlank { null },
                                birthYear = editBirthYear.toIntOrNull(),
                                ownerName = editOwner.trim().ifBlank { null },
                                stallBox = editStallBox.trim().ifBlank { null },
                                description = editDescription.trim().ifBlank { null }
                            )
                            repository.updateHorse(horseId, req)
                                .onSuccess { updated ->
                                    horse = updated
                                    isSavingHorse = false
                                    showEditDialog = false
                                    feedbackMessage = "Hevosen tiedot päivitetty."
                                }
                                .onFailure { err ->
                                    isSavingHorse = false
                                    errorMessage = err.localizedMessage ?: "Tietojen päivitys epäonnistui."
                                }
                        }
                    }
                ) {
                    Text(if (isSavingHorse) "Tallennetaan..." else "Tallenna muutokset")
                }
            },
            dismissButton = {
                TextButton(enabled = !isSavingHorse, onClick = { showEditDialog = false }) {
                    Text("Peruuta")
                }
            }
        )
    }

    if (showTagDialog && horse != null) {
        AlertDialog(
            onDismissRequest = { showTagDialog = false },
            title = { Text("Liitä NFC-tagi: ${horse!!.name}") },
            text = {
                OutlinedTextField(
                    value = newTagUid,
                    onValueChange = { newTagUid = it },
                    label = { Text("NFC UID (heksamuoto)") },
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
                                repository.assignNfcTag(horseId, newTagUid.trim())
                                    .onSuccess {
                                        newTagUid = ""
                                        showTagDialog = false
                                        feedbackMessage = "NFC-tagi päivitetty."
                                        loadData()
                                    }
                                    .onFailure { err ->
                                        errorMessage = err.localizedMessage
                                    }
                            }
                        }
                    }
                ) { Text("Tallenna") }
            },
            dismissButton = {
                TextButton(onClick = { showTagDialog = false }) { Text("Peruuta") }
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = { Text(horse?.name ?: "Hevostiedot", fontWeight = FontWeight.Bold, color = KaseNavy) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Takaisin")
                    }
                },
                actions = {
                    if (horse != null) {
                        IconButton(
                            onClick = {
                                editName = horse!!.name
                                editBreed = horse!!.breed ?: ""
                                editBirthYear = horse!!.birthYear?.toString() ?: ""
                                editOwner = horse!!.ownerName ?: ""
                                editStallBox = horse!!.stallBox ?: ""
                                editDescription = horse!!.description ?: ""
                                showEditDialog = true
                            }
                        ) {
                            Icon(Icons.Default.Edit, contentDescription = "Muokkaa hevosen tietoja", tint = KaseCrimson)
                        }
                    }
                }
            )
        }
    ) { padding ->
        if (isLoading) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else if (horse != null) {
            val h = horse!!
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                if (feedbackMessage != null) {
                    Card(colors = CardDefaults.cardColors(containerColor = KaseGreen.copy(alpha = 0.12f))) {
                        Text(
                            text = feedbackMessage!!,
                            color = KaseGreen,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 12.sp,
                            modifier = Modifier.padding(12.dp)
                        )
                    }
                }
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

                // Hevosen perustiedot + muokkauspainike
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(text = h.name, fontSize = 24.sp, fontWeight = FontWeight.Bold, color = KaseNavy)
                            FilledTonalButton(
                                onClick = {
                                    editName = h.name
                                    editBreed = h.breed ?: ""
                                    editBirthYear = h.birthYear?.toString() ?: ""
                                    editOwner = h.ownerName ?: ""
                                    editStallBox = h.stallBox ?: ""
                                    editDescription = h.description ?: ""
                                    showEditDialog = true
                                }
                            ) {
                                Icon(Icons.Default.Edit, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Muokkaa tietoja", fontSize = 12.sp)
                            }
                        }

                        InfoLine("Rotu", h.breed ?: "Ei määritetty")
                        InfoLine("Syntymävuosi", h.birthYear?.toString() ?: "Ei määritetty")
                        InfoLine("Omistaja / Talli", h.ownerName ?: "Ei määritetty")
                        InfoLine("Karsina", h.stallBox ?: "Ei määritetty")
                        if (!h.description.isNullOrBlank()) {
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = h.description,
                                fontSize = 13.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f)
                            )
                        }

                        HorizontalDivider(modifier = Modifier.padding(vertical = 6.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            val tagsText = h.nfcTags.orEmpty().joinToString { it.nfcUid }.ifBlank { "Ei liitetty" }
                            Column(modifier = Modifier.weight(1f)) {
                                Text("NFC-riimutunniste", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                                Text(tagsText, fontSize = 12.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.SemiBold)
                            }
                            TextButton(onClick = { showTagDialog = true }) {
                                Text("Muuta tagi", fontSize = 12.sp)
                            }
                        }

                        if (h.name.equals("Antero", ignoreCase = true)) {
                            Text(
                                text = "Juoma-automaatti asennettu (Vain Antero)",
                                color = KasePetrol,
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 12.sp
                            )
                        }
                    }
                }

                // Muistiinpanon lisääminen suoraan hevoskortilta
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("Lisää muistiinpano hevosesta", fontWeight = FontWeight.Bold, fontSize = 15.sp, color = KaseNavy)
                            TextButton(onClick = onOpenNotes) {
                                Text("Kaikki (${notes.size}) →", fontSize = 12.sp)
                            }
                        }

                        OutlinedTextField(
                            value = quickNoteContent,
                            onValueChange = { quickNoteContent = it },
                            placeholder = { Text("Kirjoita havainto, kengitys, ruokinta tai vointi...") },
                            modifier = Modifier.fillMaxWidth(),
                            maxLines = 3
                        )

                        Button(
                            onClick = {
                                if (quickNoteContent.isNotBlank()) {
                                    isSavingNote = true
                                    errorMessage = null
                                    feedbackMessage = null
                                    scope.launch {
                                        repository.addNote(horseId, quickNoteContent.trim())
                                            .onSuccess {
                                                quickNoteContent = ""
                                                isSavingNote = false
                                                feedbackMessage = "Muistiinpano tallennettu!"
                                                repository.getNotes(horseId).onSuccess { notes = it }
                                            }
                                            .onFailure { err ->
                                                isSavingNote = false
                                                errorMessage = err.localizedMessage ?: "Muistiinpanon tallennus epäonnistui."
                                            }
                                    }
                                }
                            },
                            enabled = !isSavingNote && quickNoteContent.isNotBlank(),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.NoteAdd, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(if (isSavingNote) "Tallennetaan..." else "Tallenna muistiinpano")
                        }

                        if (notes.isNotEmpty()) {
                            HorizontalDivider()
                            Text("Viimeisimmät merkinnät:", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                            notes.take(3).forEach { note ->
                                Column(modifier = Modifier.padding(vertical = 2.dp)) {
                                    Text(text = note.content, fontSize = 13.sp)
                                    Text(
                                        text = "${note.authorUsername ?: "Käyttäjä"} • ${note.createdAt.take(16).replace("T", " ")}",
                                        fontSize = 11.sp,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
                                    )
                                }
                            }
                        }
                    }
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedButton(
                        onClick = onOpenNotes,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.NoteAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Muistiinpanot", fontSize = 12.sp)
                    }
                    OutlinedButton(
                        onClick = onOpenAnalysis,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Analytics, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Liikeanalyysit", fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun InfoLine(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(
            text = label,
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )
        Text(
            text = value,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium
        )
    }
}
