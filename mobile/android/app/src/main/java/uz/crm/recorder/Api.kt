package uz.crm.recorder

import android.content.ContentResolver
import android.net.Uri
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class ApiException(message: String, val code: Int = 0) : Exception(message)

/** CRM server bilan aloqa (faqat standart Android kutubxonalari). */
object Api {
    private fun open(url: String): HttpURLConnection {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 15_000
        conn.readTimeout = 120_000
        return conn
    }

    private fun read(conn: HttpURLConnection): JSONObject {
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val body = stream?.bufferedReader()?.use { it.readText() } ?: ""
        val json = try { JSONObject(body) } catch (e: Exception) { JSONObject() }
        if (code !in 200..299) {
            throw ApiException(json.optString("error", "HTTP $code"), code)
        }
        return json
    }

    fun login(server: String, username: String, password: String): JSONObject {
        val conn = open("$server/telephony/mobile/login/")
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
        val form = "username=" + URLEncoder.encode(username, "UTF-8") + "&password=" + URLEncoder.encode(password, "UTF-8")
        conn.outputStream.use { it.write(form.toByteArray()) }
        return read(conn)
    }

    /**
     * Yozuvni multipart so'rov bilan yuboradi. Django serveri "chunked" so'rovni qabul qilmaydi,
     * shuning uchun fayl avval vaqtinchalik faylga ko'chiriladi va aniq Content-Length bilan yuboriladi.
     */
    fun upload(
        server: String,
        token: String,
        resolver: ContentResolver,
        rec: Recording,
        cacheDir: java.io.File,
    ): JSONObject {
        val tmp = java.io.File.createTempFile("crm_upload", ".bin", cacheDir)
        try {
            resolver.openInputStream(rec.uri)?.use { input -> tmp.outputStream().use { input.copyTo(it, 64 * 1024) } }
                ?: throw ApiException("Faylni o'qib bo'lmadi")

            val boundary = "----crm" + System.currentTimeMillis()
            val head = StringBuilder()
            fun field(name: String, value: String) {
                head.append("--$boundary\r\n")
                head.append("Content-Disposition: form-data; name=\"$name\"\r\n\r\n")
                head.append(value).append("\r\n")
            }
            field("phone", rec.phone)
            field("direction", rec.direction)
            field("started_at", rec.startedMs.toString())
            field("duration", rec.durationSec.toString())
            field("client_id", rec.clientId)
            val safeName = rec.fileName.replace("\"", "").replace("\r", "").replace("\n", "")
            head.append("--$boundary\r\n")
            head.append("Content-Disposition: form-data; name=\"file\"; filename=\"$safeName\"\r\n")
            head.append("Content-Type: application/octet-stream\r\n\r\n")
            val headBytes = head.toString().toByteArray(Charsets.UTF_8)
            val tailBytes = "\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8)

            val conn = open("$server/telephony/mobile/upload/")
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.setFixedLengthStreamingMode(headBytes.size.toLong() + tmp.length() + tailBytes.size)
            conn.setRequestProperty("Authorization", "Token $token")
            conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            conn.outputStream.use { out ->
                out.write(headBytes)
                tmp.inputStream().use { it.copyTo(out, 64 * 1024) }
                out.write(tailBytes)
            }
            return read(conn)
        } finally {
            tmp.delete()
        }
    }

    @Suppress("unused")
    fun uriString(uri: Uri): String = uri.toString()
}
