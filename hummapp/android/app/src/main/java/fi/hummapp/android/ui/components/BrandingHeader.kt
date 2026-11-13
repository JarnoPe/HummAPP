package fi.hummapp.android.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import fi.hummapp.android.R
import fi.hummapp.android.ui.theme.KaseCrimson
import fi.hummapp.android.ui.theme.KaseGold
import fi.hummapp.android.ui.theme.KaseNavy

/**
 * Yhtenäinen Euroopan unionin osarahoittama ja Kaustisen seutukunnan ylätunniste.
 * Sijoitetaan mobiilisovelluksen yläosaan kaikissa näkymissä graafisen ohjeiston mukaisesti.
 */
@Composable
fun EuKaseHeaderBanner(modifier: Modifier = Modifier) {
    Surface(
        color = Color.White,
        tonalElevation = 0.dp,
        modifier = modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .statusBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Image(
                    painter = painterResource(id = R.drawable.eu_osarahoittama_logo),
                    contentDescription = "Euroopan unionin osarahoittama",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier
                        .height(38.dp)
                        .weight(1f, fill = false)
                )
                Spacer(modifier = Modifier.width(12.dp))
                Image(
                    painter = painterResource(id = R.drawable.kase_logo),
                    contentDescription = "Kaustisen seutukunta",
                    contentScale = ContentScale.Fit,
                    modifier = Modifier
                        .height(38.dp)
                        .weight(1f, fill = false)
                )
            }
            // Kaustisen seutukunnan kolmivärinen ohut korostusviiva
            Row(modifier = Modifier.fillMaxWidth().height(3.dp)) {
                Box(modifier = Modifier.weight(1f).fillMaxHeight().background(KaseGold))
                Box(modifier = Modifier.weight(1f).fillMaxHeight().background(KaseCrimson))
                Box(modifier = Modifier.weight(2f).fillMaxHeight().background(KaseNavy))
            }
        }
    }
}
