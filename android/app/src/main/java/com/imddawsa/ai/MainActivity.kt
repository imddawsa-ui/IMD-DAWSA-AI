package com.imddawsa.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { IMDApp() }
    }
}

private data class ChatLine(val role: String, val text: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun IMDApp() {
    var endpoint by remember { mutableStateOf("http://10.0.2.2:8000") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }
    var authToken by remember { mutableStateOf("") }
    var mfaChallenge by remember { mutableStateOf("") }
    var mfaCode by remember { mutableStateOf("") }
    var totpSecret by remember { mutableStateOf("") }
    var recoveryCodes by remember { mutableStateOf("") }
    var accountStatus by remember { mutableStateOf("أنشئ حساباً أو سجّل الدخول. يلزم تأكيد البريد أولاً.") }
    var prompt by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("غير متصل — أدخل عنوان خادم الكمبيوتر") }
    var lines by remember { mutableStateOf(listOf(ChatLine("assistant", "مرحباً بك في IMD DAWSA AI. اربط خادمك المحلي لإرسال الرسائل."))) }
    val scope = rememberCoroutineScope()

    MaterialTheme {
        Scaffold(topBar = {
            TopAppBar(title = { Text("IMD DAWSA AI") }, actions = {
                Text(if (busy) "..." else "AI", modifier = Modifier.padding(end = 16.dp))
            })
        }) { padding ->
            Column(
                Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text("الحساب والأمان", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(value = endpoint, onValueChange = { endpoint = it }, label = { Text("عنوان خادم FastAPI") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                OutlinedTextField(value = email, onValueChange = { email = it }, label = { Text("البريد الإلكتروني") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                OutlinedTextField(value = password, onValueChange = { password = it }, label = { Text("كلمة المرور") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                OutlinedTextField(value = displayName, onValueChange = { displayName = it }, label = { Text("الاسم الظاهر (للتسجيل)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(enabled = !busy, onClick = {
                        scope.launch {
                            busy = true
                            try {
                                val body = JSONObject().put("email", email.trim()).put("password", password).put("display_name", displayName.trim())
                                val result = withContext(Dispatchers.IO) { postJson(endpoint.trimEnd('/'), "/api/auth/register", body) }
                                accountStatus = result.optString("message", "تحقق من بريدك الإلكتروني.")
                            } catch (e: Exception) {
                                accountStatus = "تعذر التسجيل: ${e.message}"
                            } finally { busy = false }
                        }
                    }) { Text("إنشاء حساب") }
                    Button(enabled = !busy, onClick = {
                        scope.launch {
                            busy = true
                            try {
                                val result = withContext(Dispatchers.IO) {
                                    if (mfaChallenge.isNotBlank()) {
                                        postJson(endpoint.trimEnd('/'), "/api/auth/2fa/login",
                                            JSONObject().put("challenge_token", mfaChallenge).put("code", mfaCode.trim()))
                                    } else {
                                        postJson(endpoint.trimEnd('/'), "/api/auth/login",
                                            JSONObject().put("email", email.trim()).put("password", password))
                                    }
                                }
                                if (result.optBoolean("requires_2fa")) {
                                    mfaChallenge = result.optString("challenge_token")
                                    accountStatus = "أدخل رمز تطبيق المصادقة ثم اضغط تسجيل الدخول مرة أخرى."
                                } else {
                                    authToken = result.optString("access_token")
                                    mfaChallenge = ""
                                    accountStatus = "تم تسجيل الدخول بنجاح."
                                }
                            } catch (e: Exception) {
                                accountStatus = "تعذر تسجيل الدخول: ${e.message}"
                            } finally { busy = false }
                        }
                    }) { Text(if (mfaChallenge.isBlank()) "تسجيل الدخول" else "تأكيد 2FA") }
                }
                OutlinedTextField(value = mfaCode, onValueChange = { mfaCode = it.take(6) }, label = { Text("رمز المصادقة (6 أرقام)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(enabled = authToken.isNotBlank() && !busy, onClick = {
                        scope.launch {
                            busy = true
                            try {
                                val result = withContext(Dispatchers.IO) {
                                    postJson(endpoint.trimEnd('/'), "/api/auth/2fa/setup", JSONObject(), authToken)
                                }
                                totpSecret = result.optString("secret")
                                accountStatus = "أضف هذا المفتاح يدوياً في تطبيق المصادقة ثم أدخل الرمز لتفعيله: ${totpSecret}"
                            } catch (e: Exception) {
                                accountStatus = "تعذر إعداد 2FA: ${e.message}"
                            } finally { busy = false }
                        }
                    }) { Text("إعداد 2FA") }
                    OutlinedButton(enabled = authToken.isNotBlank() && totpSecret.isNotBlank() && !busy, onClick = {
                        scope.launch {
                            busy = true
                            try {
                                val result = withContext(Dispatchers.IO) {
                                    postJson(endpoint.trimEnd('/'), "/api/auth/2fa/enable",
                                        JSONObject().put("code", mfaCode.trim()), authToken)
                                }
                                recoveryCodes = result.optJSONArray("recovery_codes")?.let { array ->
                                    (0 until array.length()).joinToString("\n") { array.getString(it) }
                                }.orEmpty()
                                accountStatus = "تم تفعيل المصادقة الثنائية. احفظ رموز الاسترداد الظاهرة أدناه."
                            } catch (e: Exception) {
                                accountStatus = "تعذر تفعيل 2FA: ${e.message}"
                            } finally { busy = false }
                        }
                    }) { Text("تفعيل 2FA") }
                    OutlinedButton(enabled = authToken.isNotBlank(), onClick = {
                        authToken = ""
                        mfaChallenge = ""
                        totpSecret = ""
                        recoveryCodes = ""
                        accountStatus = "تم تسجيل الخروج."
                    }) { Text("خروج") }
                }
                Text(accountStatus, style = MaterialTheme.typography.bodySmall)
                if (recoveryCodes.isNotBlank()) {
                    Text("رموز الاسترداد — احفظها في مكان آمن:", style = MaterialTheme.typography.labelMedium)
                    Text(recoveryCodes, style = MaterialTheme.typography.bodySmall)
                }
                Divider()
                Text("المحادثة", style = MaterialTheme.typography.titleMedium)
                Text(status, style = MaterialTheme.typography.bodySmall)
                LazyColumn(
                    Modifier.fillMaxWidth().height(300.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(lines) { line ->
                        Surface(color = if (line.role == "user") MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant, shape = RoundedCornerShape(14.dp)) {
                            Column(Modifier.fillMaxWidth().padding(12.dp)) {
                                Text(if (line.role == "user") "أنت" else "IMD DAWSA AI", style = MaterialTheme.typography.labelMedium)
                                Text(line.text)
                            }
                        }
                    }
                }
                OutlinedTextField(value = prompt, onValueChange = { prompt = it }, label = { Text("اكتب رسالتك") }, modifier = Modifier.fillMaxWidth())
                Button(
                    enabled = !busy && prompt.isNotBlank(),
                    modifier = Modifier.fillMaxWidth(),
                    onClick = {
                        val message = prompt.trim()
                        lines = lines + ChatLine("user", message)
                        prompt = ""
                        busy = true
                        status = "جارٍ الاتصال بالخادم..."
                        scope.launch {
                            try {
                                val answer = withContext(Dispatchers.IO) { sendChat(endpoint.trimEnd('/'), message, authToken) }
                                lines = lines + ChatLine("assistant", answer)
                                status = "متصل بالخادم"
                            } catch (e: Exception) {
                                lines = lines + ChatLine("assistant", "تعذر الاتصال: ${e.message ?: "تحقق من الخادم والشبكة"}")
                                status = "غير متصل"
                            } finally { busy = false }
                        }
                    }
                ) { Text(if (busy) "جارٍ الإرسال..." else "إرسال") }
                Text("تأكيد البريد يتم عبر الرابط المرسل إلى بريدك. المصادقة الثنائية تستخدم تطبيق TOTP. هذه النسخة تتصل بخادم FastAPI؛ لا تنفذ استدلالاً محلياً على الهاتف بعد.", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

private fun postJson(baseUrl: String, path: String, payload: JSONObject, bearer: String? = null): JSONObject {
    val connection = (URL("$baseUrl$path").openConnection() as HttpURLConnection).apply {
        requestMethod = "POST"
        connectTimeout = 10000
        readTimeout = 20000
        doOutput = true
        setRequestProperty("Content-Type", "application/json; charset=utf-8")
        if (!bearer.isNullOrBlank()) setRequestProperty("Authorization", "Bearer $bearer")
    }
    try {
        connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
        val code = connection.responseCode
        val body = (if (code in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (code !in 200..299) {
            val detail = try { JSONObject(body).optString("detail", body) } catch (_: Exception) { body }
            throw IllegalStateException("HTTP $code: $detail")
        }
        return JSONObject(body)
    } finally { connection.disconnect() }
}

private fun sendChat(baseUrl: String, message: String, bearer: String): String {
    val connection = (URL("$baseUrl/api/chat").openConnection() as HttpURLConnection).apply {
        requestMethod = "POST"
        connectTimeout = 5000
        readTimeout = 180000
        doOutput = true
        setRequestProperty("Content-Type", "application/json; charset=utf-8")
        if (bearer.isNotBlank()) setRequestProperty("Authorization", "Bearer $bearer")
    }
    try {
        val payload = JSONObject().put("message", message)
        connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
        val code = connection.responseCode
        val body = (if (code in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (code !in 200..299) {
            val detail = try { JSONObject(body).optString("detail", body) } catch (_: Exception) { body }
            throw IllegalStateException("HTTP $code: $detail")
        }
        return JSONObject(body).optString("reply", body)
    } finally { connection.disconnect() }
}
