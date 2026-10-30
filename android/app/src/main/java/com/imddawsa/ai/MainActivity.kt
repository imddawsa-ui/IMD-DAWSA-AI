package com.imddawsa.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
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
            Column(Modifier.fillMaxSize().padding(padding).padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("مساعدك الذكي • Android", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(value = endpoint, onValueChange = { endpoint = it }, label = { Text("عنوان خادم FastAPI") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                Text(status, style = MaterialTheme.typography.bodySmall)
                LazyColumn(Modifier.weight(1f).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
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
                                val answer = withContext(Dispatchers.IO) { sendChat(endpoint.trimEnd('/'), message) }
                                lines = lines + ChatLine("assistant", answer)
                                status = "متصل بالخادم"
                            } catch (e: Exception) {
                                lines = lines + ChatLine("assistant", "تعذر الاتصال: ${e.message ?: "تحقق من الخادم والشبكة"}")
                                status = "غير متصل"
                            } finally { busy = false }
                        }
                    }
                ) { Text(if (busy) "جارٍ الإرسال..." else "إرسال") }
                Text("الوضع المحلي على الهاتف دون إنترنت قيد التطوير؛ هذه النسخة تتصل بخادم FastAPI المحلي أو الشبكي.", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

private fun sendChat(baseUrl: String, message: String): String {
    val connection = (URL("$baseUrl/api/chat").openConnection() as HttpURLConnection).apply {
        requestMethod = "POST"
        connectTimeout = 5000
        readTimeout = 180000
        doOutput = true
        setRequestProperty("Content-Type", "application/json; charset=utf-8")
    }
    try {
        val escaped = message.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
        connection.outputStream.use { it.write("{\"message\":\"$escaped\"}".toByteArray(Charsets.UTF_8)) }
        val code = connection.responseCode
        val body = (if (code in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (code !in 200..299) throw IllegalStateException("HTTP $code: $body")
        val regex = Regex("\"reply\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"")
        return regex.find(body)?.groupValues?.get(1)
            ?.replace("\\n", "\n")?.replace("\\\"", "\"")?.replace("\\\\", "\\")
            ?: body
    } finally { connection.disconnect() }
}
