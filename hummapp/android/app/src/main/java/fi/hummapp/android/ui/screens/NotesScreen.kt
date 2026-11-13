package fi.hummapp.android.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fi.hummapp.android.data.model.HorseNote
import fi.hummapp.android.data.repository.HummRepository
import fi.hummapp.android.ui.theme.KaseGreen
import fi.hummapp.android.ui.theme.KaseNavy
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotesScreen(
    horseId: Int,
    repository: HummRepository,
    onBack: () -> Unit
) {
    var horseName by remember { mutableStateOf<String?>(null) }
    var notes by remember { mutableStateOf<List<HorseNote>>(emptyList()) }
    var newContent by remember { mutableStateOf("") }
    var isSubmitting by remember { mutableStateOf(false) }
    var feedbackMsg by remember { mutableStateOf<String?>(null) }
    var errorMsg by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun loadNotes() {
        scope.launch {
            repository.getHorses().onSuccess { list ->
                horseName = list.find { it.id == horseId }?.name
            }
            repository.getNotes(horseId).onSuccess {
                notes = it
            }.onFailure { err ->
                errorMsg = err.localizedMessage
            }
        }
    }

    LaunchedEffect(horseId) {
        loadNotes()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = {
                    Text(
                        text = if (horseName != null) "Muistiinpanot: $horseName" else "Hevoskohtaiset muistiinpanot",
                        fontWeight = FontWeight.Bold,
                        color = KaseNavy
                    )
                },
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
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            if (feedbackMsg != null) {
                Card(colors = CardDefaults.cardColors(containerColor = KaseGreen.copy(alpha = 0.12f))) {
                    Text(
                        text = feedbackMsg!!,
                        color = KaseGreen,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(10.dp)
                    )
                }
            }
            if (errorMsg != null) {
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                    Text(
                        text = errorMsg!!,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(10.dp)
                    )
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(text = "Lisää uusi muistiinpano", fontWeight = FontWeight.Bold, fontSize = 14.sp, color = KaseNavy)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = newContent,
                        onValueChange = { newContent = it },
                        placeholder = { Text("Esim. ontuu oikeaa etujalkaa, kengitys suoritettu...") },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 4
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Button(
                        onClick = {
                            if (newContent.isNotBlank()) {
                                isSubmitting = true
                                feedbackMsg = null
                                errorMsg = null
                                scope.launch {
                                    repository.addNote(horseId, newContent.trim()).onSuccess {
                                        newContent = ""
                                        isSubmitting = false
                                        feedbackMsg = "Muistiinpano tallennettu."
                                        loadNotes()
                                    }.onFailure { err ->
                                        isSubmitting = false
                                        errorMsg = err.localizedMessage ?: "Tallennus epäonnistui."
                                    }
                                }
                            }
                        },
                        enabled = !isSubmitting && newContent.isNotBlank(),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (isSubmitting) "Tallennetaan..." else "Tallenna muistiinpano")
                    }
                }
            }

            Text(text = "Aikaisemmat merkinnät (${notes.size})", fontWeight = FontWeight.Bold, color = KaseNavy)

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(notes) { note ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(text = note.content, fontSize = 13.sp)
                            Spacer(modifier = Modifier.height(4.dp))
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
    }
}
