package uz.crm.recorder

import android.content.Context
import android.content.SharedPreferences

/** Ilova sozlamalari va yuklangan fayllar ro'yxati. */
class Prefs(context: Context) {
    private val sp: SharedPreferences = context.getSharedPreferences("crm", Context.MODE_PRIVATE)

    var server: String
        get() = sp.getString("server", "") ?: ""
        set(v) = sp.edit().putString("server", v.trim().trimEnd('/')).apply()

    var token: String
        get() = sp.getString("token", "") ?: ""
        set(v) = sp.edit().putString("token", v).apply()

    var userName: String
        get() = sp.getString("name", "") ?: ""
        set(v) = sp.edit().putString("name", v).apply()

    /** Shu vaqtdan (ms) keyingi yozuvlar yuklanadi — eski shaxsiy yozuvlar yuborilmaydi. */
    var sinceMs: Long
        get() = sp.getLong("since", 0L)
        set(v) = sp.edit().putLong("since", v).apply()

    var lastSync: Long
        get() = sp.getLong("last_sync", 0L)
        set(v) = sp.edit().putLong("last_sync", v).apply()

    var uploadedCount: Int
        get() = sp.getInt("uploaded_count", 0)
        set(v) = sp.edit().putInt("uploaded_count", v).apply()

    /** Avtomatik yuborish (standart: o'chiq — foydalanuvchi o'zi tanlab yuboradi). */
    var autoUpload: Boolean
        get() = sp.getBoolean("auto_upload", false)
        set(v) = sp.edit().putBoolean("auto_upload", v).apply()

    /** Ruxsat kamida bir marta so'ralganmi (butunlay rad etilganini aniqlash uchun). */
    var askedCallLog: Boolean
        get() = sp.getBoolean("asked_call_log", false)
        set(v) = sp.edit().putBoolean("asked_call_log", v).apply()

    fun unmarkDone(id: String) {
        val set = HashSet(sp.getStringSet("done", emptySet())!!)
        if (set.remove(id)) sp.edit().putStringSet("done", set).apply()
    }

    fun error(id: String): String? = sp.getString("err_$id", null)

    fun setError(id: String, message: String?) {
        if (message == null) sp.edit().remove("err_$id").apply() else sp.edit().putString("err_$id", message).apply()
    }

    /** Telefon papkasidagi yozuv uchun qo'lda tanlangan qo'ng'iroq: "raqam|yo'nalish|boshlanish|davomiylik". */
    fun override(id: String): CallEntry? {
        val parts = (sp.getString("ovr_$id", null) ?: return null).split("|")
        if (parts.size != 4) return null
        return CallEntry(parts[0], if (parts[1] == "out") android.provider.CallLog.Calls.OUTGOING_TYPE else android.provider.CallLog.Calls.INCOMING_TYPE,
            parts[2].toLong(), parts[3].toLong())
    }

    fun setOverride(id: String, call: CallEntry) {
        sp.edit().putString("ovr_$id", "${call.number}|${call.direction}|${call.start}|${call.durationSec}").apply()
    }

    val loggedIn: Boolean get() = token.isNotEmpty() && server.isNotEmpty()

    fun isDone(id: String): Boolean = sp.getStringSet("done", emptySet())!!.contains(id)

    fun markDone(id: String) {
        val set = HashSet(sp.getStringSet("done", emptySet())!!)
        set.add(id)
        // Juda kattalashib ketmasligi uchun (eski fayllar baribir sinceMs dan oldin)
        val trimmed = if (set.size > 3000) set.toList().takeLast(2000).toHashSet() else set
        sp.edit().putStringSet("done", trimmed).apply()
    }

    fun log(): List<String> = (sp.getString("log", "") ?: "").split("\n").filter { it.isNotBlank() }

    fun addLog(line: String) {
        val lines = (listOf(line) + log()).take(30)
        sp.edit().putString("log", lines.joinToString("\n")).apply()
    }

    fun logout() {
        sp.edit().remove("token").remove("name").apply()
    }
}
