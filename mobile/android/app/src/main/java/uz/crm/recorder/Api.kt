package uz.crm.recorder

import android.content.ContentResolver
import android.net.Uri
import org.json.JSONObject
import java.io.DataOutputStream
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

    fun upload(
        server: String,
        token: String,
        resolver: ContentResolver,
        rec: Recording,
    ): JSONObject {
        val boundary = "----crm" + System.currentTimeMillis()
        val conn = open("$server/telephony/mobile/upload/")
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setChunkedStreamingMode(64 * 1024)
        conn.setRequestProperty("Authorization", "Token $token")
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")

        DataOutputStream(conn.outputStream).use { out ->
            fun field(name: String, value: String) {
                out.writeBytes("--$boundary\r\n")
                out.writeBytes("Content-Disposition: form-data; name=\"$name\"\r\n\r\n")
                out.write(value.toByteArray(Charsets.UTF_8))
                out.writeBytes("\r\n")
            }
            field("phone", rec.phone)
            field("direction", rec.direction)
            field("started_at", rec.startedMs.toString())
            field("duration", rec.durationSec.toString())
            field("client_id", rec.clientId)

            val safeName = rec.fileName.replace("\"", "").replace("\r", "").replace("\n", "")
            out.writeBytes("--$boundary\r\n")
            out.write("Content-Disposition: form-data; name=\"file\"; filename=\"$safeName\"\r\n".toByteArray(Charsets.UTF_8))
            out.writeBytes("Content-Type: application/octet-stream\r\n\r\n")
            resolver.openInputStream(rec.uri)?.use { it.copyTo(out, 64 * 1024) }
                ?: throw ApiException("Faylni o'qib bo'lmadi")
            out.writeBytes("\r\n--$boundary--\r\n")
        }
        return read(conn)
    }

    @Suppress("unused")
    fun uriString(uri: Uri): String = uri.toString()
}
