package fi.hummapp.android

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavType
import androidx.navigation.compose.*
import androidx.navigation.navArgument
import fi.hummapp.android.data.auth.TokenManager
import fi.hummapp.android.data.repository.HummRepository
import fi.hummapp.android.nfc.NfcManager
import fi.hummapp.android.ui.components.EuKaseHeaderBanner
import fi.hummapp.android.ui.screens.*
import fi.hummapp.android.ui.theme.HummAppTheme
import fi.hummapp.android.ui.theme.KaseNavy

class MainActivity : ComponentActivity() {

    private lateinit var tokenManager: TokenManager
    private lateinit var repository: HummRepository
    private lateinit var nfcManager: NfcManager

    private val scannedTagUidState = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokenManager = TokenManager(applicationContext)
        repository = HummRepository(tokenManager)
        nfcManager = NfcManager(this)

        setContent {
            HummAppTheme {
                val navController = rememberNavController()
                var loggedIn by remember { mutableStateOf(tokenManager.isLoggedIn()) }
                val startDestination = if (loggedIn) "dashboard" else "login"

                val mainTabs = listOf("dashboard", "nfc_scan", "water", "horses")

                Scaffold(
                    modifier = Modifier.fillMaxSize(),
                    topBar = {
                        EuKaseHeaderBanner()
                    },
                    bottomBar = {
                        val currentBackStack by navController.currentBackStackEntryAsState()
                        val currentRoute = currentBackStack?.destination?.route
                        if (loggedIn && currentRoute in mainTabs) {
                            NavigationBar(
                                containerColor = MaterialTheme.colorScheme.surface
                            ) {
                                NavigationBarItem(
                                    selected = currentRoute == "dashboard",
                                    onClick = {
                                        navController.navigate("dashboard") {
                                            popUpTo("dashboard") { saveState = true }
                                            launchSingleTop = true
                                            restoreState = true
                                        }
                                    },
                                    icon = { Icon(Icons.Default.Dashboard, contentDescription = "Katsaus") },
                                    label = { Text("Katsaus") }
                                )
                                NavigationBarItem(
                                    selected = currentRoute == "nfc_scan",
                                    onClick = {
                                        navController.navigate("nfc_scan") {
                                            popUpTo("dashboard") { saveState = true }
                                            launchSingleTop = true
                                            restoreState = true
                                        }
                                    },
                                    icon = { Icon(Icons.Default.Videocam, contentDescription = "NFC & Video") },
                                    label = { Text("NFC & Video") }
                                )
                                NavigationBarItem(
                                    selected = currentRoute == "water",
                                    onClick = {
                                        navController.navigate("water") {
                                            popUpTo("dashboard") { saveState = true }
                                            launchSingleTop = true
                                            restoreState = true
                                        }
                                    },
                                    icon = { Icon(Icons.Default.WaterDrop, contentDescription = "Juominen") },
                                    label = { Text("Juominen") }
                                )
                                NavigationBarItem(
                                    selected = currentRoute == "horses",
                                    onClick = {
                                        navController.navigate("horses") {
                                            popUpTo("dashboard") { saveState = true }
                                            launchSingleTop = true
                                            restoreState = true
                                        }
                                    },
                                    icon = { Icon(Icons.Default.Pets, contentDescription = "Hevoset") },
                                    label = { Text("Hevoset") }
                                )
                            }
                        }
                    }
                ) { innerPadding ->
                    NavHost(
                        navController = navController,
                        startDestination = startDestination,
                        modifier = Modifier.padding(innerPadding)
                    ) {
                        composable("login") {
                            LoginScreen(
                                tokenManager = tokenManager,
                                repository = repository,
                                onLoginSuccess = {
                                    loggedIn = true
                                    navController.navigate("dashboard") {
                                        popUpTo("login") { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("dashboard") {
                            DashboardScreen(
                                repository = repository,
                                tokenManager = tokenManager,
                                onOpenWater = { navController.navigate("water") { launchSingleTop = true } },
                                onOpenNfc = { navController.navigate("nfc_scan") { launchSingleTop = true } },
                                onOpenHorses = { navController.navigate("horses") { launchSingleTop = true } },
                                onLogout = {
                                    tokenManager.clear()
                                    loggedIn = false
                                    navController.navigate("login") {
                                        popUpTo(0) { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("nfc_scan") {
                            NfcAndVideoScreen(
                                nfcManager = nfcManager,
                                repository = repository,
                                lastScannedUid = scannedTagUidState.value,
                                onClearScannedUid = { scannedTagUidState.value = null },
                                onOpenVideo = { clipId ->
                                    navController.navigate("video_review/$clipId")
                                }
                            )
                        }
                        composable("water") {
                            WaterDetailScreen(repository = repository)
                        }
                        composable("horses") {
                            HorseListScreen(
                                repository = repository,
                                tokenManager = tokenManager,
                                onHorseClick = { horseId ->
                                    navController.navigate("horse_detail/$horseId")
                                },
                                onNfcClick = {
                                    navController.navigate("nfc_scan") { launchSingleTop = true }
                                },
                                onLogout = {
                                    tokenManager.clear()
                                    loggedIn = false
                                    navController.navigate("login") {
                                        popUpTo(0) { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable(
                            route = "horse_detail/{horseId}",
                            arguments = listOf(navArgument("horseId") { type = NavType.IntType })
                        ) { backStackEntry ->
                            val horseId = backStackEntry.arguments?.getInt("horseId") ?: return@composable
                            HorseDetailScreen(
                                horseId = horseId,
                                repository = repository,
                                onBack = { navController.popBackStack() },
                                onOpenNotes = { navController.navigate("notes/$horseId") },
                                onOpenAnalysis = { navController.navigate("analysis/$horseId") }
                            )
                        }
                        composable(
                            route = "video_review/{clipId}",
                            arguments = listOf(navArgument("clipId") { type = NavType.IntType })
                        ) { backStackEntry ->
                            val clipId = backStackEntry.arguments?.getInt("clipId") ?: return@composable
                            VideoReviewScreen(
                                clipId = clipId,
                                repository = repository,
                                tokenManager = tokenManager,
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable(
                            route = "notes/{horseId}",
                            arguments = listOf(navArgument("horseId") { type = NavType.IntType })
                        ) { backStackEntry ->
                            val horseId = backStackEntry.arguments?.getInt("horseId") ?: return@composable
                            NotesScreen(
                                horseId = horseId,
                                repository = repository,
                                onBack = { navController.popBackStack() }
                            )
                        }
                        composable(
                            route = "analysis/{horseId}",
                            arguments = listOf(navArgument("horseId") { type = NavType.IntType })
                        ) { backStackEntry ->
                            val horseId = backStackEntry.arguments?.getInt("horseId") ?: return@composable
                            AnalysisScreen(
                                horseId = horseId,
                                repository = repository,
                                onBack = { navController.popBackStack() }
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        nfcManager.enableForegroundDispatch(this)
    }

    override fun onPause() {
        super.onPause()
        nfcManager.disableForegroundDispatch(this)
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent != null) {
            val uid = nfcManager.processIntent(intent)
            if (uid != null) {
                scannedTagUidState.value = uid
                Toast.makeText(this, "NFC-tagi luettu: $uid", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
