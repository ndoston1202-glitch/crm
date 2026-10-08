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

    /** Avtomatik yuborish yoqilgan bo'lsa — har 15 daqiqada, internet bo'lganda. */
    fun schedule(context: Context) {
        val scheduler = context.getSystemService(JobScheduler::class.java)
        if (!Prefs(context).autoUpload) {
            scheduler.cancel(JOB_ID)
            return
        }
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

    /** Ilovadagi barcha yozuvlar: telefon papkasidagilar + «Ulashish» orqali kelganlar, yangilari tepada. */
    fun allItems(context: Context): List<Item> {
        val prefs = Prefs(context)
        return (Scanner(context).scan(prefs.sinceMs) + Store(context).shared()).sortedByDescending { it.startedMs }
    }

    /** Berilgan yozuvlarni yuboradi. Natija matnini qaytaradi. Fon oqimida chaqiring. */
    fun send(context: Context, items: List<Item>): String = synchronized(lock) {
        val prefs = Prefs(context)
        if (!prefs.loggedIn) return "Kirilmagan"
        val time = SimpleDateFormat("dd.MM HH:mm", Locale.getDefault()).format(Date())
        var ok = 0
        var failed = 0
        var lastError = ""
        for (item in items) {
            if (item.phone.isBlank()) {
                failed++
                lastError = "raqami tanlanmagan"
                continue
            }
            try {
                Api.upload(prefs.server, prefs.token, context.contentResolver, item.toRecording(), context.cacheDir)
                prefs.markDone(item.key)
                prefs.setError(item.key, null)
                prefs.uploadedCount = prefs.uploadedCount + 1
                ok++
            } catch (e: ApiException) {
                failed++
                lastError = e.message ?: "xato"
                prefs.setError(item.key, lastError)
                if (e.code == 401) {
                    prefs.logout()
                    break
                }
            } catch (e: Exception) {
                failed++
                lastError = "${e.javaClass.simpleName}: ${e.message ?: ""}"
                prefs.setError(item.key, lastError)
                if (e is java.io.IOException) break // tarmoq yo'q — qolganini ham yubora olmaymiz
            }
        }
        prefs.lastSync = System.currentTimeMillis()
        val summary = "Yuborildi: $ok" + if (failed > 0) ", yuborilmadi: $failed ($lastError)" else ""
        prefs.addLog("$time  $summary".take(200))
        summary
    }

    /** Fon rejimi (faqat avtomatik yuborish yoqilganda): raqami aniq va hali yuborilmagan yozuvlar. */
    fun runAuto(context: Context): String {
        val prefs = Prefs(context)
        if (!prefs.autoUpload) return "Avtomatik yuborish o'chiq"
        val pending = allItems(context).filter { !prefs.isDone(it.key) && it.phone.isNotBlank() }
        return if (pending.isEmpty()) "Yangi yozuv yo'q" else send(context, pending)
    }
}
