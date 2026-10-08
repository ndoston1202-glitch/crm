package uz.crm.recorder

import android.app.AlertDialog
import android.content.Context
import android.provider.CallLog
import android.text.InputType
import android.widget.EditText
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.abs

data class CallEntry(val number: String, val type: Int, val start: Long, val durationSec: Long) {
    val end: Long get() = start + durationSec * 1000
    val direction: String get() = if (type == CallLog.Calls.OUTGOING_TYPE) "out" else "in"
}

/** Qo'ng'iroqlar jurnali bilan ishlash. */
object Calls {
    fun load(context: Context, sinceMs: Long = 0L, limit: Int = 500): List<CallEntry> {
        val list = ArrayList<CallEntry>()
        try {
            context.contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION),
                "${CallLog.Calls.DATE} >= ? AND ${CallLog.Calls.DURATION} > 0", arrayOf(sinceMs.toString()),
                "${CallLog.Calls.DATE} DESC",
            )?.use { c ->
                while (c.moveToNext() && list.size < limit) {
                    val number = c.getString(0) ?: continue
                    list.add(CallEntry(number, c.getInt(1), c.getLong(2), c.getLong(3)))
                }
            }
        } catch (e: SecurityException) {
            // ruxsat berilmagan
        }
        return list
    }

    /** Fayl o'zgartirilgan vaqti qo'ng'iroq tugashiga eng yaqin (±3 daqiqa) bo'lgan qo'ng'iroq. */
    fun match(calls: List<CallEntry>, fileModifiedMs: Long, audioMs: Long): CallEntry? {
        val window = 3 * 60 * 1000L
        return calls
            .map { it to abs(it.end - fileModifiedMs) }
            .filter { it.second <= window }
            .minByOrNull { (call, diff) -> diff + abs(call.durationSec * 1000 - audioMs) / 4 }
            ?.first
    }

    fun label(call: CallEntry): String {
        val fmt = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault())
        val arrow = if (call.type == CallLog.Calls.OUTGOING_TYPE) "↗" else "↙"
        return "$arrow  ${call.number}   ${fmt.format(Date(call.start))} · ${call.durationSec / 60}:${"%02d".format(call.durationSec % 60)}"
    }

    /** Oxirgi qo'ng'iroqlardan birini tanlash oynasi (raqamni qo'lda kiritish ham mumkin). */
    fun pick(context: Context, title: String, onPicked: (CallEntry) -> Unit) {
        val calls = load(context, limit = 40)
        if (calls.isEmpty()) {
            manual(context, title, "Qo'ng'iroqlar jurnali bo'sh yoki ruxsat berilmagan. Mijoz raqamini kiriting:", onPicked)
            return
        }
        AlertDialog.Builder(context).setTitle(title)
            .setItems(calls.map { label(it) }.toTypedArray()) { _, which -> onPicked(calls[which]) }
            .setNeutralButton("Raqamni qo'lda kiritish") { _, _ -> manual(context, title, "Mijoz raqamini kiriting:", onPicked) }
            .setNegativeButton("Bekor qilish", null)
            .show()
    }

    private fun manual(context: Context, title: String, message: String, onPicked: (CallEntry) -> Unit) {
        val input = EditText(context).apply {
            inputType = InputType.TYPE_CLASS_PHONE
            hint = "+998 90 123 45 67"
        }
        AlertDialog.Builder(context).setTitle(title).setMessage(message).setView(input)
            .setPositiveButton("OK") { _, _ ->
                val number = input.text.toString().filter { it.isDigit() || it == '+' }
                if (number.count { it.isDigit() } >= 7) {
                    onPicked(CallEntry(number, CallLog.Calls.OUTGOING_TYPE, System.currentTimeMillis(), 0))
                } else {
                    Toast.makeText(context, "Raqam noto'g'ri", Toast.LENGTH_LONG).show()
                }
            }
            .setNegativeButton("Bekor qilish", null)
            .show()
    }
}
