package uz.crm.recorder

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.os.Build
import android.widget.Toast
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class AppRelease(val versionCode: Long, val versionName: String)

/** Ilovaning yangi versiyasini CRM serveridan tekshiradi va o'rnatadi. */
object Updater {
    fun currentVersion(context: Context): Long {
        val info = context.packageManager.getPackageInfo(context.packageName, 0)
        return if (Build.VERSION.SDK_INT >= 28) info.longVersionCode else @Suppress("DEPRECATION") info.versionCode.toLong()
    }

    fun currentName(context: Context): String =
        context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: ""

    /** Yangi versiya bo'lsa qaytaradi, aks holda null. Fon oqimida chaqiring. */
    fun check(context: Context): AppRelease? {
        val prefs = Prefs(context)
        if (!prefs.loggedIn) return null
        return try {
            val conn = URL("${prefs.server}/telephony/mobile/app/version/").openConnection() as HttpURLConnection
            conn.connectTimeout = 10_000
            conn.readTimeout = 15_000
            conn.setRequestProperty("Authorization", "Token ${prefs.token}")
            if (conn.responseCode != 200) return null
            val json = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
            val release = AppRelease(json.getLong("versionCode"), json.optString("versionName"))
            if (release.versionCode > currentVersion(context)) release else null
        } catch (e: Exception) {
            null
        }
    }

    /** APK ni yuklab, tizimning o'rnatish oynasini ochadi. Fon oqimida chaqiring. */
    fun install(context: Context) {
        val prefs = Prefs(context)
        val conn = URL("${prefs.server}/telephony/mobile/app/download/").openConnection() as HttpURLConnection
        conn.connectTimeout = 15_000
        conn.readTimeout = 120_000
        conn.setRequestProperty("Authorization", "Token ${prefs.token}")
        if (conn.responseCode != 200) throw ApiException("Yangi versiyani yuklab bo'lmadi (HTTP ${conn.responseCode})")

        val installer = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        params.setAppPackageName(context.packageName)
        val sessionId = installer.createSession(params)
        installer.openSession(sessionId).use { session ->
            conn.inputStream.use { input ->
                session.openWrite("crm.apk", 0, -1).use { out ->
                    input.copyTo(out, 64 * 1024)
                    session.fsync(out)
                }
            }
            val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
            val intent = PendingIntent.getBroadcast(context, sessionId, Intent(context, InstallReceiver::class.java), flags)
            session.commit(intent.intentSender)
        }
    }
}

/** O'rnatish natijasi: tizim foydalanuvchidan tasdiq so'rasa — tasdiqlash oynasini ochamiz. */
class InstallReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                @Suppress("DEPRECATION")
                val confirm = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                else intent.getParcelableExtra(Intent.EXTRA_INTENT) as? Intent
                confirm?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                confirm?.let { context.startActivity(it) }
            }
            PackageInstaller.STATUS_SUCCESS -> Toast.makeText(context, "Ilova yangilandi", Toast.LENGTH_LONG).show()
            else -> Toast.makeText(
                context, "Yangilab bo'lmadi: " + (intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: ""),
                Toast.LENGTH_LONG,
            ).show()
        }
    }
}
