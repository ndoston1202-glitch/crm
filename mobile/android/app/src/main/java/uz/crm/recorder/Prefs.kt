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
