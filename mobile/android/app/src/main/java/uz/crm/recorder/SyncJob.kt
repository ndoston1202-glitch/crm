package uz.crm.recorder

import android.app.job.JobParameters
import android.app.job.JobService

class SyncJob : JobService() {
    override fun onStartJob(params: JobParameters): Boolean {
        Thread {
            try {
                Sync.run(applicationContext)
            } finally {
                jobFinished(params, false)
            }
        }.start()
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean = true
}
