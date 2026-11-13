package fi.hummapp.android.nfc

import android.app.Activity
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Build

class NfcManager(private val context: Context) {

    private val nfcAdapter: NfcAdapter? = NfcAdapter.getDefaultAdapter(context)

    // Debounce: Estetään saman tagin toistuva luku 5 sekunnin ikkunassa
    private var lastScannedUid: String? = null
    private var lastScannedTime: Long = 0L
    private val debounceWindowMs = 5000L

    fun isNfcSupported(): Boolean = nfcAdapter != null

    fun isNfcEnabled(): Boolean = nfcAdapter?.isEnabled == true

    fun enableForegroundDispatch(activity: Activity) {
        if (nfcAdapter == null || !nfcAdapter.isEnabled) return

        val intent = Intent(activity, activity.javaClass).apply {
            addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            PendingIntent.FLAG_MUTABLE
        } else {
            0
        }
        val pendingIntent = PendingIntent.getActivity(activity, 0, intent, flags)

        val techFilter = IntentFilter(NfcAdapter.ACTION_TECH_DISCOVERED)
        val tagFilter = IntentFilter(NfcAdapter.ACTION_TAG_DISCOVERED)
        val filters = arrayOf(techFilter, tagFilter)

        nfcAdapter.enableForegroundDispatch(activity, pendingIntent, filters, null)
    }

    fun disableForegroundDispatch(activity: Activity) {
        nfcAdapter?.disableForegroundDispatch(activity)
    }

    /**
     * Käsittelee NFC-intentin, eristää tagin ID:n ja muuntaa sen yhtenäiseksi heksamuodoksi.
     * Palauttaa UID:n tai null, jos tagia ei löytynyt tai kyseessä on debounce-kaksoisluku.
     */
    fun processIntent(intent: Intent): String? {
        val action = intent.action ?: return null
        if (action != NfcAdapter.ACTION_TECH_DISCOVERED &&
            action != NfcAdapter.ACTION_TAG_DISCOVERED &&
            action != NfcAdapter.ACTION_NDEF_DISCOVERED
        ) {
            return null
        }

        val rawId = intent.getByteArrayExtra(NfcAdapter.EXTRA_ID)
            ?: (intent.getParcelableExtra<Tag>(NfcAdapter.EXTRA_TAG))?.id
            ?: return null

        val uidHex = bytesToHex(rawId).uppercase()

        // Debounce-tarkistus
        val now = System.currentTimeMillis()
        if (uidHex == lastScannedUid && (now - lastScannedTime) < debounceWindowMs) {
            // Sama tagi luettu liian nopeasti uudelleen, sivuutetaan vahinkoluku
            return null
        }

        lastScannedUid = uidHex
        lastScannedTime = now
        return uidHex
    }

    private fun bytesToHex(bytes: ByteArray): String {
        val hexChars = "0123456789ABCDEF"
        val result = StringBuilder(bytes.size * 2)
        for (b in bytes) {
            val i = b.toInt() and 0xFF
            result.append(hexChars[i shr 4])
            result.append(hexChars[i and 0x0F])
        }
        return result.toString()
    }
}
