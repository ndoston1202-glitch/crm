package uz.crm.recorder

import android.content.ContentUris
import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.CallLog
import android.provider.MediaStore
import kotlin.math.abs

data class Recording(
    val uri: Uri,
    val clientId: String,
    val fileName: String,
    val phone: String,
    val direction: String,
    val startedMs: Long,
    val durationSec: Long,
)

data class ScanResult(val ready: List<Recording>, val noNumber: List<String>)

/**
 * Telefonning o'z qo'ng'iroq yozuvchisi saqlagan audio fayllarni topadi va
 * qo'ng'iroqlar jurnalidan (vaqt bo'yicha) mijoz raqamini aniqlaydi.
 *
 * Papkalar: Samsung "Recordings/Call", Xiaomi "MIUI/sound_recorder/call_rec",
 * Huawei/Honor "Sounds/CallRecord", Realme/Oppo "Recordings/Call Recordings" va h.k. —
 * yo'lida "call" so'zi bo'lgan barcha audio fayllar.
 */
class Scanner(private val context: Context) {

    private data class CallEntry(val number: String, val type: Int, val start: Long, val durationSec: Long) {
        val end: Long get() = start + durationSec * 1000
    }

    private fun isCallRecording(path: String): Boolean {
        val p = path.lowercase()
        return p.contains("call") || p.contains("qo'ng'iroq") || p.contains("звон") || p.contains("record/phone")
    }

    fun scan(prefs: Prefs): ScanResult {
        val calls = loadCallLog(prefs.sinceMs - 60 * 60 * 1000)
        val ready = ArrayList<Recording>()
        val noNumber = ArrayList<String>()

        val collection = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        val pathColumn = if (Build.VERSION.SDK_INT >= 29) MediaStore.Audio.Media.RELATIVE_PATH else MediaStore.Audio.Media.DATA
        val projection = arrayOf(
            MediaStore.Audio.Media._ID,
            MediaStore.Audio.Media.DISPLAY_NAME,
            MediaStore.Audio.Media.SIZE,
            MediaStore.Audio.Media.DATE_MODIFIED,
            MediaStore.Audio.Media.DURATION,
            pathColumn,
        )
        val sinceSec = prefs.sinceMs / 1000
        context.contentResolver.query(
            collection, projection,
            "${MediaStore.Audio.Media.DATE_MODIFIED} >= ?", arrayOf(sinceSec.toString()),
            "${MediaStore.Audio.Media.DATE_MODIFIED} ASC",
        )?.use { c ->
            val idCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media._ID)
            val nameCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DISPLAY_NAME)
            val sizeCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.SIZE)
            val modCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DATE_MODIFIED)
            val durCol = c.getColumnIndexOrThrow(MediaStore.Audio.Media.DURATION)
            val pathCol = c.getColumnIndexOrThrow(pathColumn)
            val now = System.currentTimeMillis()
            while (c.moveToNext()) {
                val path = (c.getString(pathCol) ?: "") + "/" + (c.getString(nameCol) ?: "")
                if (!isCallRecording(path)) continue
                val id = c.getLong(idCol)
                val size = c.getLong(sizeCol)
                val name = c.getString(nameCol) ?: "rec_$id"
                val modifiedMs = c.getLong(modCol) * 1000
                val audioMs = c.getLong(durCol)
                val clientId = "${Build.MODEL}_${id}_${size}".take(120)
                if (prefs.isDone(clientId) || size <= 0) continue
                if (now - modifiedMs < 60_000) continue // hali yozilayotgan bo'lishi mumkin

                val match = matchCall(calls, modifiedMs, audioMs)
                val phoneFromName = Regex("""\+?\d[\d\s\-]{7,}\d""").find(name)?.value?.filter { it.isDigit() || it == '+' }
                val phone = phoneFromName ?: match?.number
                if (phone.isNullOrBlank()) {
                    noNumber.add(name)
                    continue
                }
                val direction = if (match != null && match.type == CallLog.Calls.OUTGOING_TYPE) "out" else if (match != null) "in" else "out"
                ready.add(
                    Recording(
                        uri = ContentUris.withAppendedId(collection, id),
                        clientId = clientId,
                        fileName = name,
                        phone = phone,
                        direction = direction,
                        startedMs = match?.start ?: (modifiedMs - audioMs),
                        durationSec = match?.durationSec ?: (audioMs / 1000),
                    )
                )
            }
        }
        return ScanResult(ready, noNumber)
    }

    /** Fayl o'zgartirilgan vaqti qo'ng'iroq tugashiga eng yaqin (±3 daqiqa) bo'lgan qo'ng'iroq. */
    private fun matchCall(calls: List<CallEntry>, fileModifiedMs: Long, audioMs: Long): CallEntry? {
        val window = 3 * 60 * 1000L
        return calls
            .filter { it.durationSec > 0 }
            .map { it to abs(it.end - fileModifiedMs) }
            .filter { it.second <= window }
            .minByOrNull { (call, diff) -> diff + abs(call.durationSec * 1000 - audioMs) / 4 }
            ?.first
    }

    private fun loadCallLog(sinceMs: Long): List<CallEntry> {
        val list = ArrayList<CallEntry>()
        try {
            context.contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION),
                "${CallLog.Calls.DATE} >= ?", arrayOf(sinceMs.toString()),
                "${CallLog.Calls.DATE} DESC",
            )?.use { c ->
                while (c.moveToNext()) {
                    val number = c.getString(0) ?: continue
                    list.add(CallEntry(number, c.getInt(1), c.getLong(2), c.getLong(3)))
                }
            }
        } catch (e: SecurityException) {
            // Ruxsat berilmagan — faqat fayl nomidagi raqamdan foydalaniladi
        }
        return list
    }
}
