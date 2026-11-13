package fi.hummapp.android.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fi.hummapp.android.data.auth.TokenManager
import fi.hummapp.android.data.repository.HummRepository
import fi.hummapp.android.ui.theme.KaseCrimson
import fi.hummapp.android.ui.theme.KaseNavy
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    tokenManager: TokenManager,
    repository: HummRepository,
    onLoginSuccess: () -> Unit
) {
    var serverUrl by remember { mutableStateOf(tokenManager.getBaseUrl()) }
    var username by remember { mutableStateOf("admin") }
    var password by remember { mutableStateOf("Tallipaallikko2026!") }
    var isLoading by remember { mutableStateOf(false) }
    var isTestingHealth by remember { mutableStateOf(false) }
    var healthStatusMsg by remember { mutableStateOf<String?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "HummAPP",
            fontSize = 34.sp,
            fontWeight = FontWeight.Black,
            color = KaseNavy
        )
        Text(
            text = "Kaustisen seutukunnan talliseuranta",
            fontSize = 13.sp,
            color = KaseCrimson,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(bottom = 20.dp)
        )

        if (errorMessage != null) {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
            ) {
                Text(
                    text = errorMessage!!,
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    fontSize = 12.sp,
                    modifier = Modifier.padding(12.dp)
                )
            }
        }

        if (healthStatusMsg != null) {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = healthStatusMsg!!,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        fontSize = 12.sp
                    )
                }
            }
        }

        // Pikavalinnat ympäristöille
        Text(
            text = "Valitse yhteysosoite:",
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 6.dp)
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            FilterChip(
                selected = serverUrl == TokenManager.ENV_SHARED_URL,
                onClick = { serverUrl = TokenManager.ENV_SHARED_URL },
                label = { Text("Pilottiympäristö", fontSize = 11.sp) }
            )
            FilterChip(
                selected = serverUrl == TokenManager.NAS_DEFAULT_URL,
                onClick = { serverUrl = TokenManager.NAS_DEFAULT_URL },
                label = { Text("Synology NAS", fontSize = 11.sp) }
            )
        }

        OutlinedTextField(
            value = serverUrl,
            onValueChange = { serverUrl = it },
            label = { Text("Palvelimen osoite (URL)") },
            placeholder = { Text(TokenManager.ENV_SHARED_URL) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 6.dp),
            horizontalArrangement = Arrangement.End
        ) {
            TextButton(
                onClick = {
                    isTestingHealth = true
                    errorMessage = null
                    healthStatusMsg = null
                    tokenManager.saveBaseUrl(serverUrl)
                    repository.refreshApi()
                    scope.launch {
                        repository.checkHealth()
                            .onSuccess { h ->
                                isTestingHealth = false
                                healthStatusMsg = "Yhteys OK (${h.app ?: "HummAPP"} • Tietokanta: ${h.database ?: "healthy"})"
                            }
                            .onFailure { err ->
                                isTestingHealth = false
                                errorMessage = err.localizedMessage
                            }
                    }
                },
                enabled = !isTestingHealth
            ) {
                Icon(Icons.Default.CloudDone, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text(if (isTestingHealth) "Testataan..." else "Testaa yhteys", fontSize = 12.sp)
            }
        }

        Spacer(modifier = Modifier.height(6.dp))

        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text("Käyttäjätunnus") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(12.dp))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Salasana") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(20.dp))

        Button(
            onClick = {
                if (username.isBlank() || password.isBlank()) {
                    errorMessage = "Anna sekä käyttäjätunnus että salasana."
                    return@Button
                }
                isLoading = true
                errorMessage = null
                tokenManager.saveBaseUrl(serverUrl)
                repository.refreshApi()

                scope.launch {
                    val result = repository.login(username.trim(), password)
                    isLoading = false
                    result.onSuccess {
                        onLoginSuccess()
                    }.onFailure { err ->
                        errorMessage = err.localizedMessage ?: "Yhteysvirhe palvelimeen."
                    }
                }
            },
            enabled = !isLoading,
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    color = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(20.dp),
                    strokeWidth = 2.dp
                )
            } else {
                Icon(Icons.Default.Lock, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Kirjaudu sisään", fontWeight = FontWeight.Bold)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Oletustunnus pilottiin: admin / Tallipaallikko2026!",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f)
        )
    }
}
