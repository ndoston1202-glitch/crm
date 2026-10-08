package uz.crm.recorder

import android.content.ContentUris
import android.content.Context
import android.os.Build
import android.provider.MediaStore

data class Recording(
    val uri: android.net.Uri,
    val clientId: String,
    val fileName: String,
    val phone: String,
    val direction: String,
    val startedMs: Long,
    val durationSec: Long,
)

/**
 * Telefonning o'z qo'ng'iroq yozuvchisi ochiq papkaga saqlagan audio fayllarni topadi
 * (Samsung "Recordings/Call", Xiaomi "MIUI/sound_recorder/call_rec", Huawei "Sounds/CallRecord" va h.k.)
 * va qo'ng'iroqlar jurnalidan vaqt bo'yicha raqamini aniqlaydi.
 */
class Scanner(private val context: Context) {

    private fun isCallRecording(path: String): Boolean {
        val p = path.lowercase()
        return p.contains("call") || p.contains("звон") || p.contains("record/phone")
    }

    fun scan(sinceMs: Long): List<Item> {
        val calls = Calls.load(context, sinceMs - 60 * 60 * 1000)
        val result = ArrayList<Item>()
        val collection = MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        val pathColumn = if (Build.VERSION.SDK_INT >= 29) MediaStore.Audio.Media.RELATIVE_PATH else MediaStore.Audio.Media.DATA
        val projection = arrayOf(
            MediaStore.Audio.Media._ID, MediaStore.Audio.Media.DISPLAY_NAME, MediaStore.Audio.Media.SIZE,
            MediaStore.Audio.Media.DATE_MODIFIED, MediaStore.Audio.Media.DURATION, pathColumn,
        )
        try {
            context.contentResolver.query(
                collection, projection, "${MediaStore.Audio.Media.DATE_MODIFIED} >= ?",
                arrayOf((sinceMs / 1000).toString()), "${MediaStore.Audio.Media.DATE_MODIFIED} DESC",
            )?.use { c ->
                val now = System.currentTimeMillis()
                while (c.moveToNext()) {
                    val name = c.getString(1) ?: "rec_${c.getLong(0)}"
                    if (!isCallRecording((c.getString(5) ?: "") + "/" + name)) continue
                    val id = c.getLong(0)
                    val size = c.getLong(2)
                    val modifiedMs = c.getLong(3) * 1000
                    val audioMs = c.getLong(4)
                    if (size <= 0 || now - modifiedMs < 60_000) continue // hali yozilayotgan bo'lishi mumkin
                    val match = Calls.match(calls, modifiedMs, audioMs)
                    val fromName = Regex("""\+?\d[\d\s\-]{7,}\d""").find(name)?.value?.filter { it.isDigit() || it == '+' }
                    result.add(Item(
                        key = "${Build.MODEL}_${id}_${size}".take(120),
                        uri = ContentUris.withAppendedId(collection, id),
                        name = name,
                        phone = fromName ?: match?.number ?: "",
                        direction = match?.direction ?: "out",
                        startedMs = match?.start ?: (modifiedMs - audioMs),
                        durationSec = match?.durationSec ?: (audioMs / 1000),
                        shared = false,
                    ))
                }
            }
        } catch (e: SecurityException) {
            // audio fayllarga ruxsat berilmagan
        }
        return result
    }
}
