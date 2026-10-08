package uz.crm.recorder

import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object Sync {
    private const val JOB_ID = 1001
    private val lock = Any()

    /** Har 15 daqiqada (Android ruxsat bergan eng qisqa oraliq), internet bo'lganda ishlaydi. */
    fun schedule(context: Context) {
        val scheduler = context.getSystemService(JobScheduler::class.java)
        val job = JobInfo.Builder(JOB_ID, ComponentName(context, SyncJob::class.java))
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPeriodic(15 * 60 * 1000L)
            .setPersisted(true)
            .build()
        scheduler.schedule(job)
    }

    fun cancel(context: Context) {
        context.getSystemService(JobScheduler::class.java).cancel(JOB_ID)
    }

    /** Yangi yozuvlarni topib yuklaydi. Natija matnini qaytaradi. Fon oqimida chaqiring. */
    fun run(context: Context): String = synchronized(lock) {
        val prefs = Prefs(context)
        if (!prefs.loggedIn) return "Kirilmagan"
        val time = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault()).format(Date())
        val result = try {
            Scanner(context).scan(prefs)
        } catch (e: SecurityException) {
            prefs.addLog("$time  Ruxsat yo'q: fayllar yoki qo'ng'iroqlar jurnali")
            return "Ruxsat berilmagan"
        }
        var ok = 0
        var failed = 0
        for (rec in result.ready) {
            try {
                Api.upload(prefs.server, prefs.token, context.contentResolver, rec, context.cacheDir)
                prefs.markDone(rec.clientId)
                prefs.uploadedCount = prefs.uploadedCount + 1
                ok++
                prefs.addLog("$time  ✓ ${rec.phone} (${rec.durationSec / 60}:${"%02d".format(rec.durationSec % 60)})")
            } catch (e: ApiException) {
                failed++
                if (e.code == 401) {
                    prefs.logout()
                    prefs.addLog("$time  Sessiya tugagan — qayta kiring")
                    break
                }
                if (e.code == 400) prefs.markDone(rec.clientId) // noto'g'ri ma'lumot — qayta urinishdan foyda yo'q
                prefs.addLog("$time  ✗ ${rec.phone}: ${e.message}")
            } catch (e: Exception) {
                failed++
                prefs.addLog("$time  ✗ ${rec.phone}: ${e.javaClass.simpleName} ${e.message ?: ""}".take(160))
                break // internet yo'q — keyingi safar
            }
        }
        prefs.lastSync = System.currentTimeMillis()
        val summary = "Yuklandi: $ok" +
            (if (failed > 0) ", xato: $failed" else "") +
            (if (result.noNumber.isNotEmpty()) ", raqami topilmadi: ${result.noNumber.size}" else "")
        if (ok > 0 || failed > 0) prefs.addLog("$time  $summary")
        summary
    }
}
