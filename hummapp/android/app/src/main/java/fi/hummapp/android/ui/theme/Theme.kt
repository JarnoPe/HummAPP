package fi.hummapp.android.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Kaustisen seutukunnan graafinen ohjeisto
val KaseNavy = Color(0xFF1B325E)
val KaseCrimson = Color(0xFFC60651)
val KaseGold = Color(0xFFFDBE4F)
val KaseGoldLight = Color(0xFFFFDCA3)
val KaseGreen = Color(0xFF00A34D)
val KasePetrol = Color(0xFF135367)
val KaseSky = Color(0xFFC0E1F0)
val KaseOrange = Color(0xFFF89628)
val KaseBrick = Color(0xFFA1342C)
val KaseGray80 = Color(0xFF58595B)
val KaseGray70 = Color(0xFF6D6E71)
val KaseGray50 = Color(0xFF939598)
val KaseBackground = Color(0xFFF8FAFC)

private val LightColorScheme = lightColorScheme(
    primary = KaseNavy,
    onPrimary = Color.White,
    primaryContainer = KaseSky,
    onPrimaryContainer = KaseNavy,
    secondary = KasePetrol,
    onSecondary = Color.White,
    secondaryContainer = KaseGoldLight,
    onSecondaryContainer = KaseGray80,
    tertiary = KaseCrimson,
    onTertiary = Color.White,
    background = KaseBackground,
    onBackground = KaseGray80,
    surface = Color.White,
    onSurface = KaseGray80,
    surfaceVariant = Color(0xFFF1F5F9),
    onSurfaceVariant = KaseGray70,
    error = KaseBrick,
    onError = Color.White
)

@Composable
fun HummAppTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        content = content
    )
}
