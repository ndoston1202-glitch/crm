package uz.crm.recorder

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Ilova ichidagi bitta yozuv (telefon yozuvchisining fayli yoki «Ulashish» orqali kelgan nusxa). */
data class Item(
    val key: String,
    val uri: Uri,
    val name: String,
    val phone: String,
    val direction: String,
    val startedMs: Long,
    val durationSec: Long,
    val shared: Boolean,
) {
    fun toRecording() = Recording(uri, key, name, phone, direction, startedMs, durationSec)
}

/** «Ulashish» orqali kelgan yozuvlar ilova papkasida saqlanadi (filesDir/recordings) va items.json da ro'yxatlanadi. */
class Store(private val context: Context) {
    private val dir = File(context.filesDir, "recordings").apply { mkdirs() }
    private val index = File(context.filesDir, "items.json")

    @Synchronized
    fun shared(): MutableList<Item> {
        if (!index.exists()) return mutableListOf()
        val arr = try { JSONArray(index.readText()) } catch (e: Exception) { JSONArray() }
        val list = mutableListOf<Item>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            val file = File(dir, o.getString("file"))
            if (!file.exists()) continue
            list.add(Item(o.getString("key"), Uri.fromFile(file), o.getString("name"), o.optString("phone"),
                o.optString("direction", "out"), o.optLong("started"), o.optLong("duration"), true))
        }
        return list
    }

    @Synchronized
    private fun save(items: List<Item>) {
        val arr = JSONArray()
        for (it in items) {
            arr.put(JSONObject().put("key", it.key).put("file", File(it.uri.path!!).name).put("name", it.name)
                .put("phone", it.phone).put("direction", it.direction).put("started", it.startedMs).put("duration", it.durationSec))
        }
        index.writeText(arr.toString())
    }

    /** Boshqa ilovadan kelgan faylni ilova ichiga ko'chiradi. */
    @Synchronized
    fun addShared(source: Uri, name: String): Item {
        val now = System.currentTimeMillis()
        val safe = name.replace(Regex("[^\\w.\\-]"), "_").takeLast(80)
        val file = File(dir, "${now}_$safe")
        context.contentResolver.openInputStream(source)?.use { input -> file.outputStream().use { input.copyTo(it) } }
            ?: throw IllegalStateException("Faylni o'qib bo'lmadi")
        val item = Item("share_${android.os.Build.MODEL}_${now}_${file.length()}".take(120), Uri.fromFile(file), name,
            "", "out", now, 0, true)
        save(shared() + item)
        return item
    }

    @Synchronized
    fun update(item: Item) {
        save(shared().map { if (it.key == item.key) item else it })
    }

    @Synchronized
    fun delete(item: Item) {
        item.uri.path?.let { File(it).delete() }
        save(shared().filter { it.key != item.key })
    }
}
