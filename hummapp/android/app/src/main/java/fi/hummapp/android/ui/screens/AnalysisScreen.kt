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
import fi.hummapp.android.data.model.AnalysisCreateRequest
import fi.hummapp.android.data.model.MovementAnalysis
import fi.hummapp.android.data.repository.HummRepository
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AnalysisScreen(
    horseId: Int,
    repository: HummRepository,
    onBack: () -> Unit
) {
    var analyses by remember { mutableStateOf<List<MovementAnalysis>>(emptyList()) }
    var method by remember { mutableStateOf("Ulkoisen palvelun analyysi") }
    var summary by remember { mutableStateOf("") }
    var isSubmitting by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun loadAnalyses() {
        scope.launch {
            repository.getAnalyses(horseId).onSuccess {
                analyses = it
            }
        }
    }

    LaunchedEffect(horseId) {
        loadAnalyses()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                windowInsets = WindowInsets(0.dp),
                title = { Text("Liikeanalyysien tulokset") },
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
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Text(text = "Tallenna analyysin tulos", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = method,
                        onValueChange = { method = it },
                        label = { Text("Menetelmä tai palvelu") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = summary,
                        onValueChange = { summary = it },
                        label = { Text("Yhteenveto tuloksista") },
                        placeholder = { Text("Symmetrinen askellus, ei epäpuhtauksia ravissa...") },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 3
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Button(
                        onClick = {
                            if (summary.isNotBlank()) {
                                isSubmitting = true
                                scope.launch {
                                    val req = AnalysisCreateRequest(
                                        horseId = horseId,
                                        analysisMethod = method.trim(),
                                        summary = summary.trim()
                                    )
                                    repository.addAnalysis(req).onSuccess {
                                        summary = ""
                                        isSubmitting = false
                                        loadAnalyses()
                                    }.onFailure {
                                        isSubmitting = false
                                    }
                                }
                            }
                        },
                        enabled = !isSubmitting && summary.isNotBlank(),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Tallenna tulos")
                    }
                }
            }

            Text(text = "Tallennetut tulokset (${analyses.size})", fontWeight = FontWeight.Bold)

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(analyses) { item ->
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(text = item.analysisMethod, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                SuggestionChip(
                                    onClick = {},
                                    label = { Text(item.status, fontSize = 10.sp) }
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(text = item.summary, fontSize = 12.sp)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = item.analysisTimestamp.take(16),
                                fontSize = 10.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                            )
                        }
                    }
                }
            }
        }
    }
}
