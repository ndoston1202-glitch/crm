package uz.crm.recorder

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.media.MediaPlayer
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : Activity() {
    companion object {
        const val EXTRA_ASSIGN = "assign_key"
    }

    private lateinit var prefs: Prefs
    private val blue = Color.parseColor("#2F6FE4")
    private val ink = Color.parseColor("#1F2D3D")
    private var items: List<Item> = emptyList()
    private val selected = HashSet<String>()
    private var showAll = false
    private var player: MediaPlayer? = null
    private var playingKey: String? = null
    private var release: AppRelease? = null
    private var pendingAssign: String? = null
    private var scroll: ScrollView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        pendingAssign = intent.getStringExtra(EXTRA_ASSIGN)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        pendingAssign = intent.getStringExtra(EXTRA_ASSIGN)
    }

    override fun onResume() {
        super.onResume()
        if (prefs.loggedIn) {
            reload()
            checkUpdate()
        } else {
            showLogin()
        }
    }

    override fun onPause() {
        super.onPause()
        stopPlayer()
    }

    // ---------- Ruxsatlar ----------
    private fun neededPermissions(): Array<String> {
        val list = mutableListOf(Manifest.permission.READ_CALL_LOG)
        list += if (Build.VERSION.SDK_INT >= 33) Manifest.permission.READ_MEDIA_AUDIO else Manifest.permission.READ_EXTERNAL_STORAGE
        return list.toTypedArray()
    }

    private fun missingPermissions() = neededPermissions().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (prefs.loggedIn) reload()
    }

    // ---------- UI yordamchilari ----------
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun page(): LinearLayout {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(24))
        }
        val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        head.addView(ImageView(this).apply {
            setImageResource(R.mipmap.ic_launcher)
            layoutParams = LinearLayout.LayoutParams(dp(44), dp(44))
        })
        head.addView(text("CRM yozuvlar", 20f, bold = true).apply { setPadding(dp(12), 0, 0, 0) })
        root.addView(head)
        // Ekran qayta chizilganda ro'yxat tepaga sakramasligi uchun joriy holatni saqlaymiz
        val y = scroll?.scrollY ?: 0
        val sv = ScrollView(this).apply { addView(root); setBackgroundColor(Color.parseColor("#F4F6F9")) }
        setContentView(sv)
        sv.post { sv.scrollTo(0, y) }
        scroll = sv
        return root
    }

    private fun text(s: String, size: Float = 15f, bold: Boolean = false, color: Int = ink) = TextView(this).apply {
        text = s
        textSize = size
        setTextColor(color)
        if (bold) typeface = Typeface.DEFAULT_BOLD
        setPadding(0, dp(2), 0, dp(2))
    }

    private fun input(hint: String, value: String = "", type: Int = InputType.TYPE_CLASS_TEXT) = EditText(this).apply {
        this.hint = hint
        setText(value)
        inputType = type
        setSingleLine()
    }

    private fun button(label: String, primary: Boolean = true, small: Boolean = false, onClick: () -> Unit) = Button(this).apply {
        text = label
        isAllCaps = false
        textSize = if (small) 13f else 16f
        setTextColor(if (primary) Color.WHITE else blue)
        background = GradientDrawable().apply {
            cornerRadius = dp(10).toFloat()
            if (primary) setColor(blue) else { setColor(Color.WHITE); setStroke(dp(1), blue) }
        }
        layoutParams = if (small) LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, dp(38)).apply { marginEnd = dp(6) }
        else LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(50)).apply { topMargin = dp(10) }
        if (small) setPadding(dp(12), 0, dp(12), 0)
        setOnClickListener { onClick() }
    }

    private fun card(vararg views: View) = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(14), dp(10), dp(14), dp(10))
        background = GradientDrawable().apply { cornerRadius = dp(12).toFloat(); setColor(Color.WHITE) }
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
            .apply { topMargin = dp(10) }
        views.forEach { addView(it) }
    }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_LONG).show()

    // ---------- Kirish ----------
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
                    if (prefs.sinceMs == 0L) prefs.sinceMs = System.currentTimeMillis() - 7 * 24 * 60 * 60 * 1000L
                    runOnUiThread {
                        Sync.schedule(this)
                        val missing = missingPermissions()
                        if (missing.isNotEmpty()) requestPermissions(missing.toTypedArray(), 1)
                        reload()
                        checkUpdate()
                    }
                } catch (e: ApiException) {
                    runOnUiThread { toast(e.message ?: "Xato") }
                } catch (e: Exception) {
                    runOnUiThread { toast("Serverga ulanib bo'lmadi: manzil va Wi-Fi ni tekshiring") }
                }
            }.start()
        })
    }

    // ---------- Ro'yxat ----------
    private fun reload() {
        Thread {
            val list = Sync.allItems(this).map { item ->
                // qo'lda tanlangan qo'ng'iroq (telefon papkasidagi yozuvlar uchun)
                if (item.shared) item else prefs.override(item.key)?.let {
                    item.copy(phone = it.number, direction = it.direction, startedMs = it.start, durationSec = it.durationSec)
                } ?: item
            }
            runOnUiThread {
                items = list
                selected.retainAll(list.map { it.key }.toSet())
                showMain()
                pendingAssign?.let { key ->
                    pendingAssign = null
                    items.firstOrNull { it.key == key }?.let { assignCall(it, offerSend = true) }
                }
            }
        }.start()
    }

    private fun checkUpdate() {
        Thread {
            val r = Updater.check(this)
            runOnUiThread {
                if (r != null && release?.versionCode != r.versionCode) {
                    release = r
                    showMain()
                }
            }
        }.start()
    }

    private fun showMain() {
        val root = page()
        val fmt = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault())

        release?.let { r ->
            root.addView(card(
                text("Yangi versiya: ${r.versionName}", 16f, bold = true, color = Color.parseColor("#198754")),
                text("Hozirgi: ${Updater.currentName(this)}", 13f, color = Color.GRAY),
                button("Ilovani yangilash") { installUpdate() },
            ))
        }

        root.addView(text("${prefs.userName} · ${prefs.server}", 13f, color = Color.GRAY).apply { setPadding(0, dp(8), 0, 0) })

        val missing = missingPermissions()
        if (missing.isNotEmpty()) {
            root.addView(card(
                text("Ruxsat berilmagan: qo'ng'iroqlar jurnali yoki audio fayllar", 14f, color = Color.parseColor("#DC3545")),
                button("Ruxsat berish") { requestPermissions(missing.toTypedArray(), 1) },
            ))
        }

        val visible = items.filter { showAll || !prefs.isDone(it.key) }
        val pendingCount = items.count { !prefs.isDone(it.key) }

        // Asosiy amal
        root.addView(button("Tanlanganlarni yuborish (${selected.size})") { sendSelected() }.apply {
            isEnabled = selected.isNotEmpty()
            alpha = if (selected.isNotEmpty()) 1f else .5f
        })

        val bar = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(0, dp(8), 0, 0) }
        bar.addView(button(if (visible.isNotEmpty() && visible.all { it.key in selected }) "Belgini olish" else "Hammasini belgilash",
            primary = false, small = true) {
            if (visible.all { it.key in selected }) selected.removeAll(visible.map { it.key }.toSet())
            else selected.addAll(visible.filter { it.phone.isNotBlank() }.map { it.key })
            showMain()
        })
        bar.addView(button(if (showAll) "Faqat yuborilmaganlar" else "Hammasini ko'rsatish", primary = false, small = true) {
            showAll = !showAll
            showMain()
        })
        bar.addView(button("↻", primary = false, small = true) { reload() })
        root.addView(bar)

        root.addView(text(
            if (showAll) "Jami yozuvlar: ${items.size}, yuborilmagan: $pendingCount" else "Yuborilmagan yozuvlar: $pendingCount",
            13f, color = Color.GRAY,
        ).apply { setPadding(0, dp(8), 0, 0) })

        if (visible.isEmpty()) {
            root.addView(card(
                text("Yozuvlar yo'q", 15f, bold = true),
                text("Google «Telefon» ishlatsangiz: qo'ng'iroqlar tarixi → qo'ng'iroq → yozuv → «Поделиться» → «CRM ga yuklash». " +
                    "Yozuv shu ro'yxatga tushadi.", 13f),
            ))
        }

        for (item in visible) root.addView(row(item, fmt))

        // Sozlamalar
        val auto = Switch(this).apply {
            text = "Avtomatik yuborish (har 15 daqiqada)"
            textSize = 14f
            isChecked = prefs.autoUpload
            setOnCheckedChangeListener { _, on ->
                prefs.autoUpload = on
                Sync.schedule(this@MainActivity)
            }
        }
        root.addView(card(
            text("Sozlamalar", 15f, bold = true),
            auto,
            text("O'chiq bo'lsa, yozuvlarni o'zingiz belgilab yuborasiz.", 12f, color = Color.GRAY),
            text("Yuborilgan yozuvlar: ${prefs.uploadedCount}" +
                (if (prefs.lastSync > 0) " · oxirgisi ${fmt.format(Date(prefs.lastSync))}" else ""), 13f),
            text("Ilova versiyasi: ${Updater.currentName(this)}", 13f, color = Color.GRAY),
        ))
        root.addView(button("Batareya sozlamalari", primary = false) {
            try {
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_SETTINGS))
            }
        })
        val log = prefs.log()
        if (log.isNotEmpty()) root.addView(card(text("Jurnal", 15f, bold = true), *log.take(10).map { text(it, 12f) }.toTypedArray()))
        root.addView(button("Chiqish", primary = false) {
            Sync.cancel(this)
            prefs.logout()
            showLogin()
        })
    }

    private fun row(item: Item, fmt: SimpleDateFormat): View {
        val done = prefs.isDone(item.key)
        val error = prefs.error(item.key)
        val check = CheckBox(this).apply {
            isChecked = item.key in selected
            isEnabled = item.phone.isNotBlank()
            setOnCheckedChangeListener { _, on ->
                if (on) selected.add(item.key) else selected.remove(item.key)
                showMain()
            }
        }
        val arrow = if (item.direction == "out") "↗" else "↙"
        val info = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            addView(text(if (item.phone.isNotBlank()) "$arrow ${item.phone}" else "Raqam tanlanmagan", 16f, bold = true,
                color = if (item.phone.isNotBlank()) ink else Color.parseColor("#DC3545")))
            val dur = if (item.durationSec > 0) " · ${item.durationSec / 60}:${"%02d".format(item.durationSec % 60)}" else ""
            addView(text("${fmt.format(Date(item.startedMs))}$dur" + if (item.shared) " · ulashilgan" else "", 13f, color = Color.GRAY))
            addView(when {
                done -> text("✓ Yuborilgan", 13f, color = Color.parseColor("#198754"))
                error != null -> text("✗ $error", 12f, color = Color.parseColor("#DC3545"))
                else -> text("● Yuborilmagan", 13f, color = Color.parseColor("#B7791F"))
            })
        }
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(check)
            addView(info)
        }
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(dp(40), dp(4), 0, 0) }
        actions.addView(button(if (playingKey == item.key) "■ To'xtatish" else "▶ Tinglash", primary = false, small = true) { togglePlay(item) })
        actions.addView(button(if (item.phone.isBlank()) "Raqamni tanlash" else "Raqam", primary = false, small = true) {
            assignCall(item, offerSend = false)
        })
        if (item.shared) actions.addView(button("🗑", primary = false, small = true) {
            AlertDialog.Builder(this).setMessage("Yozuv ilovadan o'chirilsinmi?")
                .setPositiveButton("O'chirish") { _, _ -> Store(this).delete(item); selected.remove(item.key); reload() }
                .setNegativeButton("Yo'q", null).show()
        })
        return card(top, actions)
    }

    // ---------- Amallar ----------
    private fun assignCall(item: Item, offerSend: Boolean) {
        Calls.pick(this, "Yozuv qaysi qo'ng'iroqqa tegishli?") { call ->
            if (item.shared) {
                Store(this).update(item.copy(phone = call.number, direction = call.direction, startedMs = call.start, durationSec = call.durationSec))
            } else {
                prefs.setOverride(item.key, call)
            }
            prefs.setError(item.key, null)
            if (offerSend) {
                AlertDialog.Builder(this).setTitle(call.number).setMessage("Yozuv CRM ga hozir yuborilsinmi?")
                    .setPositiveButton("Yuborish") { _, _ -> selected.clear(); selected.add(item.key); reloadThenSend() }
                    .setNegativeButton("Keyinroq") { _, _ -> reload() }
                    .show()
            } else {
                selected.add(item.key)
                reload()
            }
        }
    }

    private fun reloadThenSend() {
        Thread {
            val fresh = Sync.allItems(this).map { item ->
                if (item.shared) item else prefs.override(item.key)?.let {
                    item.copy(phone = it.number, direction = it.direction, startedMs = it.start, durationSec = it.durationSec)
                } ?: item
            }
            runOnUiThread { items = fresh; sendSelected() }
        }.start()
    }

    private fun sendSelected() {
        val toSend = items.filter { it.key in selected }
        if (toSend.isEmpty()) return
        toast("Yuborilmoqda: ${toSend.size} ta...")
        Thread {
            val result = Sync.send(this, toSend)
            runOnUiThread {
                selected.removeAll(toSend.filter { prefs.isDone(it.key) }.map { it.key }.toSet())
                AlertDialog.Builder(this).setMessage(result).setPositiveButton("OK", null).show()
                if (prefs.loggedIn) reload() else showLogin()
            }
        }.start()
    }

    private fun togglePlay(item: Item) {
        val wasPlaying = playingKey == item.key
        stopPlayer()
        if (!wasPlaying) {
            try {
                player = MediaPlayer().apply {
                    setDataSource(this@MainActivity, item.uri)
                    setOnCompletionListener { stopPlayer(); showMain() }
                    prepare()
                    start()
                }
                playingKey = item.key
            } catch (e: Exception) {
                toast("Ijro etib bo'lmadi: ${e.message}")
            }
        }
        showMain()
    }

    private fun stopPlayer() {
        player?.release()
        player = null
        playingKey = null
    }

    private fun installUpdate() {
        toast("Yangi versiya yuklanmoqda...")
        Thread {
            try {
                Updater.install(this)
            } catch (e: Exception) {
                runOnUiThread {
                    AlertDialog.Builder(this).setTitle("Yangilab bo'lmadi").setMessage(e.message ?: e.javaClass.simpleName)
                        .setPositiveButton("OK", null).show()
                }
            }
        }.start()
    }
}
