package uz.crm.recorder

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : Activity() {
    private lateinit var prefs: Prefs
    private val blue = Color.parseColor("#2F6FE4")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
    }

    override fun onResume() {
        super.onResume()
        if (prefs.loggedIn) showMain() else showLogin()
    }

    private fun neededPermissions(): Array<String> {
        val list = mutableListOf(Manifest.permission.READ_CALL_LOG)
        list += if (Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_AUDIO else Manifest.permission.READ_EXTERNAL_STORAGE
        return list.toTypedArray()
    }

    private fun missingPermissions() = neededPermissions().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (prefs.loggedIn) {
            showMain()
            if (missingPermissions().isEmpty()) syncNow()
        }
    }

    // ---------- UI yordamchilari ----------
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun page(): LinearLayout {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(24))
        }
        root.addView(ImageView(this).apply {
            setImageResource(R.mipmap.ic_launcher)
            layoutParams = LinearLayout.LayoutParams(dp(72), dp(72)).apply { gravity = Gravity.CENTER_HORIZONTAL }
        })
        root.addView(text("CRM yozuvlar", 22f, bold = true).apply { gravity = Gravity.CENTER; setPadding(0, dp(8), 0, dp(16)) })
        setContentView(ScrollView(this).apply { addView(root); setBackgroundColor(Color.parseColor("#F4F6F9")) })
        return root
    }

    private fun text(s: String, size: Float = 15f, bold: Boolean = false, color: Int = Color.parseColor("#1F2D3D")) =
        TextView(this).apply {
            text = s
            textSize = size
            setTextColor(color)
            if (bold) typeface = Typeface.DEFAULT_BOLD
            setPadding(0, dp(4), 0, dp(4))
        }

    private fun input(hint: String, value: String = "", type: Int = InputType.TYPE_CLASS_TEXT) = EditText(this).apply {
        this.hint = hint
        setText(value)
        inputType = type
        setSingleLine()
    }

    private fun button(label: String, primary: Boolean = true, onClick: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        textSize = 16f
        setTextColor(if (primary) Color.WHITE else blue)
        background = GradientDrawable().apply {
            cornerRadius = dp(10).toFloat()
            if (primary) setColor(blue) else { setColor(Color.WHITE); setStroke(dp(1), blue) }
        }
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(50)).apply { topMargin = dp(10) }
        setOnClickListener { onClick() }
    }

    private fun card(vararg views: View) = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(16), dp(12), dp(16), dp(12))
        background = GradientDrawable().apply { cornerRadius = dp(12).toFloat(); setColor(Color.WHITE) }
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            .apply { topMargin = dp(12) }
        views.forEach { addView(it) }
    }

    // ---------- Kirish ekrani ----------
    private fun showLogin() {
        val root = page()
        val server = input("Server manzili, masalan http://192.168.1.10:8000", prefs.server, InputType.TYPE_TEXT_VARIATION_URI)
        val user = input("Login")
        val pass = input("Parol", type = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD)
        root.addView(card(text("CRM ga kirish", 17f, bold = true), server, user, pass))
        root.addView(button("Kirish") {
            var url = server.text.toString().trim().trimEnd('/')
            if (url.isNotEmpty() && !url.startsWith("http")) url = "http://$url"
            if (url.isEmpty() || user.text.isBlank() || pass.text.isEmpty()) {
                toast("Hamma maydonlarni to'ldiring")
                return@button
            }
            Thread {
                try {
                    val res = Api.login(url, user.text.toString().trim(), pass.text.toString())
                    prefs.server = url
                    prefs.token = res.getString("token")
                    prefs.userName = res.optString("name")
                    // Faqat kirgandan keyingi (va oxirgi 1 kunlik) yozuvlar yuklanadi
                    if (prefs.sinceMs == 0L) prefs.sinceMs = System.currentTimeMillis() - 24 * 60 * 60 * 1000L
                    runOnUiThread {
                        Sync.schedule(this)
                        val missing = missingPermissions()
                        if (missing.isNotEmpty()) requestPermissions(missing.toTypedArray(), 1) else { showMain(); syncNow() }
                    }
                } catch (e: ApiException) {
                    runOnUiThread { toast(e.message ?: "Xato") }
                } catch (e: Exception) {
                    runOnUiThread { toast("Serverga ulanib bo'lmadi: manzil va internetni tekshiring") }
                }
            }.start()
        })
    }

    // ---------- Asosiy ekran ----------
    private fun showMain() {
        val root = page()
        val fmt = SimpleDateFormat("dd.MM.yyyy HH:mm", Locale.getDefault())
        val last = if (prefs.lastSync > 0) fmt.format(Date(prefs.lastSync)) else "—"
        val missing = missingPermissions()

        root.addView(card(
            text(prefs.userName, 18f, bold = true),
            text(prefs.server, 13f, color = Color.GRAY),
            text("Yuklangan yozuvlar: ${prefs.uploadedCount}"),
            text("Oxirgi tekshiruv: $last"),
            text(
                if (missing.isEmpty()) "● Fonda ishlayapti (har 15 daqiqada)" else "● Ruxsatlar berilmagan",
                color = Color.parseColor(if (missing.isEmpty()) "#198754" else "#DC3545"),
            ),
        ))

        if (missing.isNotEmpty()) {
            root.addView(button("Ruxsat berish") { requestPermissions(missing.toTypedArray(), 1) })
        }
        root.addView(button("Hozir yuklash") { syncNow() })

        root.addView(card(
            text("Muhim", 15f, bold = true),
            text("1. Telefon sozlamalarida qo'ng'iroqlarni avtomatik yozish yoqilgan bo'lsin (Telefon → Sozlamalar → Qo'ng'iroqlarni yozish).", 13f),
            text("2. Xiaomi, Huawei, Oppo va boshqalarda ilovaga batareya cheklovini o'chiring, aks holda fonda ishlamaydi.", 13f),
            text("3. Google «Telefon» ilovasi yozuvlarni boshqa ilovalarga bermaydi. U holda: qo'ng'iroqlar tarixi → qo'ng'iroq → yozuv → «Ulashish» → «CRM ga yuklash» → qo'ng'iroqni tanlang.", 13f),
        ))
        root.addView(button("Batareya sozlamalari", primary = false) {
            try {
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_SETTINGS))
            }
        })

        val log = prefs.log()
        if (log.isNotEmpty()) {
            root.addView(card(text("Jurnal", 15f, bold = true), *log.map { text(it, 13f) }.toTypedArray()))
        }
        root.addView(button("Chiqish", primary = false) {
            Sync.cancel(this)
            prefs.logout()
            showLogin()
        })
    }

    private fun syncNow() {
        toast("Tekshirilmoqda...")
        Thread {
            val result = Sync.run(applicationContext)
            runOnUiThread {
                toast(result)
                if (prefs.loggedIn) showMain() else showLogin()
            }
        }.start()
    }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_LONG).show()
}
