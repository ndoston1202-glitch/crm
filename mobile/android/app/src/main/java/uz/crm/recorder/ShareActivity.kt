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
import android.provider.CallLog
import android.provider.OpenableColumns
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Boshqa ilovadan (masalan Google «Telefon») "Ulashish" orqali kelgan qo'ng'iroq yozuvini qabul qiladi.
 * Yozuv qaysi qo'ng'iroqqa tegishli ekanini foydalanuvchi oxirgi qo'ng'iroqlar ro'yxatidan tanlaydi.
 */
class ShareActivity : Activity() {
    private lateinit var prefs: Prefs
    private var audio: Uri? = null

    private data class CallItem(val number: String, val type: Int, val start: Long, val durationSec: Long)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        audio = sharedUri(intent)
        if (!prefs.loggedIn) {
            toast("Avval CRM yozuvlar ilovasiga kiring")
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }
        if (audio == null) {
            toast("Fayl topilmadi")
            finish()
            return
        }
        if (checkSelfPermission(Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.READ_CALL_LOG), 2)
        } else {
            show()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        show()
    }

    @Suppress("DEPRECATION")
    private fun sharedUri(intent: Intent): Uri? {
        if (intent.action != Intent.ACTION_SEND) return null
        return if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        else intent.getParcelableExtra(Intent.EXTRA_STREAM) as? Uri
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun recentCalls(): List<CallItem> {
        val list = ArrayList<CallItem>()
        try {
            contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION),
                "${CallLog.Calls.DURATION} > 0", null, "${CallLog.Calls.DATE} DESC",
            )?.use { c ->
                while (c.moveToNext() && list.size < 30) {
                    val number = c.getString(0) ?: continue
                    list.add(CallItem(number, c.getInt(1), c.getLong(2), c.getLong(3)))
                }
            }
        } catch (e: SecurityException) {
            // ruxsat berilmagan
        }
        return list
    }

    private fun show() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(20), dp(16), dp(20))
        }
        root.addView(TextView(this).apply {
            text = "Yozuv qaysi qo'ng'iroqqa tegishli?"
            textSize = 19f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.parseColor("#1F2D3D"))
        })
        root.addView(TextView(this).apply {
            text = "Ro'yxatdan qo'ng'iroqni tanlang — yozuv shu raqamning lidiga yuklanadi."
            setTextColor(Color.GRAY)
            setPadding(0, dp(4), 0, dp(12))
        })
        val calls = recentCalls()
        if (calls.isEmpty()) {
            root.addView(TextView(this).apply {
                text = "Qo'ng'iroqlar jurnali bo'sh yoki ruxsat berilmagan."
                setTextColor(Color.parseColor("#DC3545"))
            })
        }
        val fmt = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault())
        for (call in calls) {
            val arrow = if (call.type == CallLog.Calls.OUTGOING_TYPE) "↗" else "↙"
            root.addView(TextView(this).apply {
                text = "$arrow  ${call.number}\n${fmt.format(Date(call.start))} · ${call.durationSec / 60}:${"%02d".format(call.durationSec % 60)}"
                textSize = 16f
                setTextColor(Color.parseColor("#1F2D3D"))
                setPadding(dp(16), dp(12), dp(16), dp(12))
                gravity = Gravity.START
                background = GradientDrawable().apply { cornerRadius = dp(12).toFloat(); setColor(Color.WHITE) }
                layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                    .apply { topMargin = dp(8) }
                setOnClickListener { upload(call) }
            })
        }
        setContentView(ScrollView(this).apply { addView(root); setBackgroundColor(Color.parseColor("#F4F6F9")) })
    }

    private fun fileInfo(uri: Uri): Pair<String, Long> {
        var name = "yozuv.m4a"
        var size = 0L
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)?.use { c ->
            if (c.moveToFirst()) {
                c.getString(0)?.let { name = it }
                if (!c.isNull(1)) size = c.getLong(1)
            }
        }
        return name to size
    }

    private fun upload(call: CallItem) {
        val uri = audio ?: return
        toast("Yuklanmoqda...")
        Thread {
            val result = try {
                val (name, size) = fileInfo(uri)
                val rec = Recording(
                    uri = uri,
                    clientId = "share_${Build.MODEL}_${call.start}_$size".take(120),
                    fileName = name,
                    phone = call.number,
                    direction = if (call.type == CallLog.Calls.OUTGOING_TYPE) "out" else "in",
                    startedMs = call.start,
                    durationSec = call.durationSec,
                )
                Api.upload(prefs.server, prefs.token, contentResolver, rec)
                prefs.uploadedCount = prefs.uploadedCount + 1
                val time = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault()).format(Date())
                prefs.addLog("$time  ✓ ${call.number} (ulashildi)")
                "Yuklandi: ${call.number}"
            } catch (e: ApiException) {
                if (e.code == 401) prefs.logout()
                "Xato: ${e.message}"
            } catch (e: Exception) {
                "Serverga ulanib bo'lmadi"
            }
            runOnUiThread {
                toast(result)
                if (result.startsWith("Yuklandi")) finish()
            }
        }.start()
    }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_LONG).show()
}
