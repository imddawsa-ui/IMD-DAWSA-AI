package com.imddawsa.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.Color
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { NileOneApp() }
    }
}

private data class FeedItem(val id: Int, val author: String, val content: String, val likes: Int, val comments: Int)
private data class MarketItem(val id: Int, val title: String, val description: String, val price: String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NileOneApp() {
    val context = LocalContext.current
    val preferences = remember { context.getSharedPreferences("nile_one_preferences", android.content.Context.MODE_PRIVATE) }
    var endpoint by remember { mutableStateOf("") }
    val languageOptions = listOf("ar" to "العربية", "en" to "English", "fr" to "Français", "es" to "Español", "pt" to "Português", "sw" to "Kiswahili", "am" to "አማርኛ", "so" to "Soomaali", "ha" to "Hausa", "zh" to "中文", "hi" to "हिन्दी", "ur" to "اردو", "bn" to "বাংলা", "ru" to "Русский", "de" to "Deutsch", "it" to "Italiano", "tr" to "Türkçe", "id" to "Bahasa Indonesia", "ja" to "日本語", "ko" to "한국어", "fa" to "فارسی", "ps" to "پښتو", "nl" to "Nederlands", "pl" to "Polski", "uk" to "Українська", "zu" to "isiZulu", "rw" to "Kinyarwanda", "lg" to "Luganda")
    var languageCode by remember {
        mutableStateOf(
            preferences.getString("preferred_language", null)
                ?: languageOptions.firstOrNull { it.first == java.util.Locale.getDefault().language }?.first
                ?: "en"
        )
    }
    var languageMenuOpen by remember { mutableStateOf(false) }
    val themeOptions = listOf("aurora" to "Aurora Dark", "light" to "Studio Light", "purple" to "Nebula Purple", "emerald" to "Emerald Focus")
    var themeName by remember { mutableStateOf(preferences.getString("preferred_theme", "aurora") ?: "aurora") }
    var themeMenuOpen by remember { mutableStateOf(false) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var mfaChallenge by remember { mutableStateOf("") }
    var mfaCode by remember { mutableStateOf("") }
    var accountStatus by remember { mutableStateOf("أدخل عنوان خادم NILE ONE HUMAN ثم سجّل الدخول.") }
    var activeTab by remember { mutableStateOf("الرئيسية") }
    var prompt by remember { mutableStateOf("") }
    var postText by remember { mutableStateOf("") }
    var marketTitle by remember { mutableStateOf("") }
    var marketDescription by remember { mutableStateOf("") }
    var chatLines by remember { mutableStateOf(listOf<Pair<String,String>>()) }
    var feed by remember { mutableStateOf(listOf<FeedItem>()) }
    var listings by remember { mutableStateOf(listOf<MarketItem>()) }
    var generalStatus by remember { mutableStateOf("لم يتم الاتصال بالخادم بعد.") }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun base(): String = endpoint.trim().trimEnd('/')
    fun requireEndpoint() { require(base().startsWith("http://") || base().startsWith("https://")) { "أدخل عنوان الخادم كاملاً ويبدأ بـ http:// أو https://" } }
    fun loadFeed() {
        scope.launch {
            busy = true
            try {
                requireEndpoint()
                val result = withContext(Dispatchers.IO) { getJson(base(), "/api/social/feed", token) }
                val a = result.optJSONArray("items") ?: JSONArray()
                feed = (0 until a.length()).map { i -> a.getJSONObject(i).let { FeedItem(it.optInt("id"), it.optString("display_name","مستخدم"), it.optString("content"), it.optInt("like_count"), it.optInt("comment_count")) } }
                generalStatus = "تم تحديث المجتمع: ${feed.size} منشور"
            } catch (e: Exception) { generalStatus = "تعذر تحميل المجتمع: ${e.message}" }
            finally { busy = false }
        }
    }
    fun loadMarket() {
        scope.launch {
            busy = true
            try {
                requireEndpoint()
                val result = withContext(Dispatchers.IO) { getJson(base(), "/api/marketplace/listings", token) }
                val a = result.optJSONArray("items") ?: JSONArray()
                listings = (0 until a.length()).map { i -> a.getJSONObject(i).let { MarketItem(it.optInt("id"), it.optString("title"), it.optString("description"), if (it.isNull("price_amount")) "السعر عند الطلب" else "${it.optString("price_amount")} ${it.optString("currency","USD")}") } }
                generalStatus = "تم تحديث السوق: ${listings.size} عرض"
            } catch (e: Exception) { generalStatus = "تعذر تحميل السوق: ${e.message}" }
            finally { busy = false }
        }
    }

    val appColorScheme = when (themeName) {
        "light" -> lightColorScheme(primary = Color(0xFF315B8A), secondary = Color(0xFF557A70), background = Color(0xFFF4F6FA), surface = Color(0xFFFFFFFF))
        "purple" -> darkColorScheme(primary = Color(0xFFC5A3FF), secondary = Color(0xFF8DCEFF), background = Color(0xFF171326), surface = Color(0xFF241D38))
        "emerald" -> darkColorScheme(primary = Color(0xFF76D7B0), secondary = Color(0xFFA9D8C4), background = Color(0xFF101E1A), surface = Color(0xFF1A2D26))
        else -> darkColorScheme(primary = Color(0xFF8CCBFF), secondary = Color(0xFFB6C8FF), background = Color(0xFF101923), surface = Color(0xFF1A2937))
    }
    MaterialTheme(colorScheme = appColorScheme) {
        Scaffold(topBar = { TopAppBar(title = { Text("NILE ONE HUMAN") }, actions = { Text(if (token.isBlank()) "زائر" else "متصل", modifier = Modifier.padding(end = 16.dp)) }) },
            bottomBar = {
                NavigationBar {
                    listOf("الرئيسية","AI","المجتمع","السوق","الحساب").forEach { tab ->
                        NavigationBarItem(selected = activeTab == tab, onClick = {
                            activeTab = tab
                            if (tab == "المجتمع") loadFeed()
                            if (tab == "السوق") loadMarket()
                        }, icon = { Text(when(tab) { "الرئيسية" -> "⌂"; "AI" -> "✦"; "المجتمع" -> "◎"; "السوق" -> "▣"; else -> "●" }) }, label = { Text(tab) })
                    }
                }
            }
        ) { padding ->
            Column(Modifier.fillMaxSize().padding(padding).padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Text("🌍 Language")
                    Box {
                        OutlinedButton(onClick = { languageMenuOpen = true }) { Text(languageOptions.firstOrNull { it.first == languageCode }?.second ?: languageCode) }
                        DropdownMenu(expanded = languageMenuOpen, onDismissRequest = { languageMenuOpen = false }) {
                            languageOptions.forEach { option -> DropdownMenuItem(text = { Text(option.second) }, onClick = { languageCode = option.first; preferences.edit().putString("preferred_language", option.first).apply(); languageMenuOpen = false; generalStatus = "تم حفظ اللغة: " + option.second + ". ترجمة الردود تتطلب إعداد محرك ترجمة على الخادم." }) }
                        }
                    }
                    Spacer(Modifier.width(4.dp))
                    Box {
                        OutlinedButton(onClick = { themeMenuOpen = true }) { Text("Theme") }
                        DropdownMenu(expanded = themeMenuOpen, onDismissRequest = { themeMenuOpen = false }) {
                            themeOptions.forEach { option -> DropdownMenuItem(text = { Text(option.second) }, onClick = { themeName = option.first; preferences.edit().putString("preferred_theme", option.first).apply(); themeMenuOpen = false }) }
                        }
                    }
                }
                when(activeTab) {
                    "الرئيسية" -> {
                        Text("منصة واحدة لخدماتك الرقمية والذكاء الاصطناعي", style = MaterialTheme.typography.titleLarge)
                        Text("لوحة NILE ONE HUMAN", style = MaterialTheme.typography.titleMedium)
                        Text("الأقسام المتاحة في هذا الإصدار: مساعد AI، مجتمع المنشورات، السوق، الحساب والأمان.")
                        Text("أقسام قيد التطوير: الصوت والفيديو، إنشاء الصور، التطبيقات المدمجة، QUANT LAB، المدفوعات ومساحات الشركات. لا يتم عرضها كخدمات عاملة قبل اكتمال الربط.")
                        OutlinedTextField(value = endpoint, onValueChange = { endpoint = it }, label = { Text("عنوان خادم FastAPI (HTTPS للنشر)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                        Button(enabled = !busy, onClick = {
                            scope.launch {
                                busy = true
                                try { requireEndpoint(); val h = withContext(Dispatchers.IO) { getJson(base(), "/api/health", "") }; val ready = withContext(Dispatchers.IO) { getJson(base(), "/api/readiness", "") }; generalStatus = "الخادم: ${h.optString("status")} · AI جاهز: ${ready.optBoolean("ready")} · المزود: ${ready.optString("provider")}" }
                                catch(e:Exception) { generalStatus = "فشل فحص الخادم: ${e.message}" }
                                finally { busy = false }
                            }
                        }) { Text("فحص اتصال الخادم") }
                        Text(generalStatus)
                    }
                    "AI" -> {
                        Text("مساعد NILE ONE AI", style = MaterialTheme.typography.titleLarge)
                        Text("تُرسل الرسائل إلى /api/chat في خادمك. يحتاج الخادم إلى نموذج Ollama أو مزود متوافق مُهيأ.")
                        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(chatLines) { (who,msg) -> Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(12.dp)) { Text(who, style = MaterialTheme.typography.labelMedium); Text(msg) } } }
                        }
                        OutlinedTextField(value = prompt, onValueChange = { prompt = it }, label = { Text("اكتب سؤالك") }, modifier = Modifier.fillMaxWidth())
                        Button(enabled = !busy && prompt.isNotBlank(), modifier = Modifier.fillMaxWidth(), onClick = {
                            val msg = prompt.trim(); prompt = ""; chatLines = chatLines + ("أنت" to msg); busy = true
                            scope.launch {
                                try { requireEndpoint(); val res = withContext(Dispatchers.IO) { postJson(base(), "/api/chat", JSONObject().put("message",msg), token) }; var answer = res.optString("reply","لم يرجع الخادم إجابة")
                                    try {
                                        val translated = withContext(Dispatchers.IO) { postJson(base(), "/api/i18n/translate", JSONObject().put("text", answer).put("source", "auto").put("target", languageCode), null) }
                                        answer = translated.optString("translated_text", answer)
                                        generalStatus = "اكتملت الإجابة مع الترجمة."
                                    } catch (_: Exception) {
                                        generalStatus = "الرد الأصلي معروض؛ الترجمة غير متاحة حتى يتم إعداد محرك ترجمة مجاني على الخادم."
                                    }
                                    chatLines = chatLines + ("NILE ONE AI · " + res.optString("model","AI") to answer) }
                                catch(e:Exception) { chatLines = chatLines + ("النظام" to "تعذر تنفيذ الطلب: ${e.message}") }
                                finally { busy = false }
                            }
                        }) { Text(if (busy) "جارٍ التفكير..." else "إرسال") }
                    }
                    "المجتمع" -> {
                        Text("المجتمع", style = MaterialTheme.typography.titleLarge)
                        OutlinedTextField(value = postText, onValueChange = { postText = it }, label = { Text("اكتب منشوراً") }, modifier = Modifier.fillMaxWidth())
                        Button(enabled = !busy && postText.isNotBlank() && token.isNotBlank(), onClick = {
                            busy = true; scope.launch {
                                try { requireEndpoint(); withContext(Dispatchers.IO) { postJson(base(), "/api/social/posts", JSONObject().put("content",postText.trim()).put("visibility","public"), token) }; postText = ""; loadFeed() }
                                catch(e:Exception) { generalStatus = "تعذر نشر المنشور: ${e.message}"; busy = false }
                            }
                        }) { Text("نشر") }
                        Row { Button(onClick = { loadFeed() }, enabled = !busy) { Text("تحديث") }; Text(generalStatus, Modifier.padding(8.dp)) }
                        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(feed) { item -> Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(12.dp)) { Text(item.author, style = MaterialTheme.typography.titleSmall); Text(item.content); Text("♥ ${item.likes}   تعليقات ${item.comments}", style = MaterialTheme.typography.labelSmall) } } }
                        }
                        if (token.isBlank()) Text("تسجيل الدخول مطلوب لنشر المحتوى.")
                    }
                    "السوق" -> {
                        Text("السوق", style = MaterialTheme.typography.titleLarge)
                        OutlinedTextField(value = marketTitle, onValueChange = { marketTitle = it }, label = { Text("عنوان العرض الجديد") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(value = marketDescription, onValueChange = { marketDescription = it }, label = { Text("وصف العرض") }, modifier = Modifier.fillMaxWidth())
                        Button(enabled = !busy && token.isNotBlank() && marketTitle.length >= 3, onClick = {
                            busy = true; scope.launch {
                                try { requireEndpoint(); withContext(Dispatchers.IO) { postJson(base(), "/api/marketplace/listings", JSONObject().put("title",marketTitle.trim()).put("description",marketDescription.trim()).put("category","general").put("currency","USD"), token) }; marketTitle = ""; marketDescription = ""; loadMarket() }
                                catch(e:Exception) { generalStatus = "تعذر إنشاء العرض: ${e.message}"; busy = false }
                            }
                        }) { Text("إضافة عرض") }
                        Row { Button(onClick = { loadMarket() }, enabled = !busy) { Text("تحديث السوق") }; Text(generalStatus, Modifier.padding(8.dp)) }
                        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(listings) { item -> Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(12.dp)) { Text(item.title, style = MaterialTheme.typography.titleMedium); Text(item.description); Text(item.price) } } }
                        }
                    }
                    else -> {
                        Text("الحساب والأمان", style = MaterialTheme.typography.titleLarge)
                        OutlinedTextField(value = email, onValueChange = { email = it }, label = { Text("البريد الإلكتروني") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                        OutlinedTextField(value = password, onValueChange = { password = it }, label = { Text("كلمة المرور (10 أحرف على الأقل)") }, modifier = Modifier.fillMaxWidth(), visualTransformation = PasswordVisualTransformation(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password))
                        OutlinedTextField(value = displayName, onValueChange = { displayName = it }, label = { Text("الاسم الظاهر") }, modifier = Modifier.fillMaxWidth())
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(enabled = !busy, onClick = {
                                busy = true; scope.launch {
                                    try { requireEndpoint(); val res = withContext(Dispatchers.IO) { postJson(base(), "/api/auth/register", JSONObject().put("email",email.trim()).put("password",password).put("display_name",displayName.trim())) }; accountStatus = res.optString("message","تحقق من بريدك الإلكتروني لتفعيل الحساب.") }
                                    catch(e:Exception) { accountStatus = "تعذر التسجيل: ${e.message}" }
                                    finally { busy = false }
                                }
                            }) { Text("إنشاء حساب") }
                            Button(enabled = !busy, onClick = {
                                busy = true; scope.launch {
                                    try {
                                        requireEndpoint()
                                        val res = withContext(Dispatchers.IO) { if (mfaChallenge.isNotBlank()) postJson(base(),"/api/auth/2fa/login",JSONObject().put("challenge_token",mfaChallenge).put("code",mfaCode),null) else postJson(base(),"/api/auth/login",JSONObject().put("email",email.trim()).put("password",password)) }
                                        if (res.optBoolean("requires_2fa")) { mfaChallenge = res.optString("challenge_token"); accountStatus = "أدخل رمز المصادقة ثم سجّل الدخول مجدداً." }
                                        else { token = res.optString("access_token"); mfaChallenge = ""; accountStatus = if(token.isNotBlank()) "تم تسجيل الدخول." else "لم يرجع الخادم رمز جلسة." }
                                    } catch(e:Exception) { accountStatus = "تعذر تسجيل الدخول: ${e.message}" }
                                    finally { busy = false }
                                }
                            }) { Text(if(mfaChallenge.isBlank()) "تسجيل الدخول" else "تأكيد 2FA") }
                        }
                        OutlinedTextField(value = mfaCode, onValueChange = { mfaCode = it.take(6) }, label = { Text("رمز المصادقة (6 أرقام)") }, modifier = Modifier.fillMaxWidth())
                        Button(enabled = token.isNotBlank(), onClick = { token = ""; mfaChallenge = ""; accountStatus = "تم تسجيل الخروج." }) { Text("خروج") }
                        Text(accountStatus)
                        if(token.isNotBlank()) Text("الجلسة نشطة. يمكن استخدام المجتمع والسوق والميزات المحمية.")
                    }
                }
            }
        }
    }
}

private fun requestJson(baseUrl: String, path: String, method: String, payload: JSONObject? = null, bearer: String? = null): JSONObject {
    val c = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
        requestMethod = method; connectTimeout = 10000; readTimeout = 180000
        setRequestProperty("Accept","application/json")
        if(payload != null) { doOutput = true; setRequestProperty("Content-Type","application/json; charset=utf-8") }
        if(!bearer.isNullOrBlank()) setRequestProperty("Authorization","Bearer $bearer")
    }
    try {
        if(payload != null) c.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
        val code = c.responseCode
        val body = (if(code in 200..299) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() }.orEmpty()
        if(code !in 200..299) { val detail = try { JSONObject(body).optString("detail",body) } catch(_:Exception) { body }; throw IllegalStateException("HTTP $code: $detail") }
        return if(body.isBlank()) JSONObject() else JSONObject(body)
    } finally { c.disconnect() }
}
private fun getJson(base: String, path: String, bearer: String? = null) = requestJson(base,path,"GET",null,bearer)
private fun postJson(base: String, path: String, payload: JSONObject, bearer: String? = null) = requestJson(base,path,"POST",payload,bearer)
