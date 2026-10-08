package uz.crm.recorder

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.OpenableColumns
import android.widget.Toast

/**
 * Boshqa ilovadan (masalan Google «Telefon») «Ulashish» orqali kelgan yozuv(lar)ni ilova ichiga saqlaydi.
 * Yozuvlar keyin asosiy ekrandagi ro'yxatda turadi — foydalanuvchi ularni tanlab yuboradi.
 */
class ShareActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val uris = sharedUris(intent)
        if (uris.isEmpty()) {
            Toast.makeText(this, "Fayl topilmadi", Toast.LENGTH_LONG).show()
            finish()
            return
        }
        val store = Store(this)
        val saved = ArrayList<String>()
        for (uri in uris) {
            try {
                saved.add(store.addShared(uri, displayName(uri)).key)
            } catch (e: Exception) {
                Toast.makeText(this, "Saqlab bo'lmadi: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
        Toast.makeText(this, "Ilovaga saqlandi: ${saved.size} ta yozuv", Toast.LENGTH_SHORT).show()
        // Bitta yozuv bo'lsa — asosiy ekranda darhol qo'ng'iroqni tanlash oynasi ochiladi
        startActivity(Intent(this, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            .putExtra(MainActivity.EXTRA_ASSIGN, if (saved.size == 1) saved[0] else null))
        finish()
    }

    @Suppress("DEPRECATION")
    private fun sharedUris(intent: Intent): List<Uri> = when (intent.action) {
        Intent.ACTION_SEND -> listOfNotNull(
            if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
            else intent.getParcelableExtra(Intent.EXTRA_STREAM) as? Uri
        )
        Intent.ACTION_SEND_MULTIPLE ->
            (if (Build.VERSION.SDK_INT >= 33) intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java)
            else intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM)) ?: emptyList()
        else -> emptyList()
    }

    private fun displayName(uri: Uri): String {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) c.getString(0)?.let { return it }
        }
        return "yozuv.m4a"
    }
}
