package com.techminds.flowbeacon

import android.app.Application
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit
import kotlin.math.roundToInt

class Snap(val d: Reading, val e: Eval, val level: Level, val issues: List<String>, val pred: String)

object Roles {
    val ALL = listOf("overview", "model", "incidents", "connect", "calib", "drip", "settings", "console")
    val NAME = mapOf("consumer" to "Consumer", "team" to "Maintenance team", "dev" to "Developer")
    val DESC = mapOf(
        "consumer" to "See drain status, live readings, the drain model and history. No controls.",
        "team" to "Full operational control: incidents, board connection and calibration.",
        "dev" to "Full control of everything, including the firmware console. Can switch to any mode. Password required."
    )
    fun tabs(role: String): List<String> = when (role) {
        "consumer" -> listOf("overview", "model", "drip", "settings")
        "team" -> ALL.filter { it != "console" }
        else -> ALL
    }
}

val WZ_STEPS = listOf("Normal flow, valve fully open", "Partial valve, about half closed", "Valve mostly closed", "Wet the rain plate")

/** All app state and logic: readings, conditions, incidents, Wi-Fi link, demo mode and Drip's mood. */
class AppVm(app: Application) : AndroidViewModel(app) {
    val prefs = Prefs(app)
    val sound = Sound(app, prefs)
    private val main = Handler(Looper.getMainLooper())
    private val http = OkHttpClient.Builder().readTimeout(0, TimeUnit.MILLISECONDS).pingInterval(20, TimeUnit.SECONDS).build()

    // ---- state the screens read ----
    var role by mutableStateOf("consumer")
    var roleChosen by mutableStateOf(false)
    var devAsk by mutableStateOf(false)
    var devMsg by mutableStateOf("")
    var chooserCancel by mutableStateOf(false)
    var cfg by mutableStateOf(prefs.cfg)
    var base by mutableStateOf(prefs.base)
    val incidents = mutableStateListOf<Incident>()
    var snap by mutableStateOf<Snap?>(null)
    var histVer by mutableStateOf(0)
    val hist = ArrayList<Sample>()
    var connected by mutableStateOf(false)
    var demo by mutableStateOf(false)
    var scen by mutableStateOf("normal")
    var connLabel by mutableStateOf("Not connected")
    var msg by mutableStateOf("")
    var banner by mutableStateOf("")
    var dripState by mutableStateOf("sleep")
    var dripRain by mutableStateOf(false)
    var dripSayText by mutableStateOf("")
    var dripOn by mutableStateOf(prefs.drip)
    var mute by mutableStateOf(prefs.mute)
    var vol by mutableStateOf(prefs.vol)
    var vibrate by mutableStateOf(prefs.vibrate)
    var accent by mutableStateOf(prefs.accent)
    var mode by mutableStateOf(prefs.mode)
    var calm by mutableStateOf(prefs.calm)
    var node by mutableStateOf(prefs.node)
    var sndVer by mutableStateOf(0)
    var recording by mutableStateOf(false)
    var recCount by mutableStateOf(0)
    private val recRows = ArrayList<String>()
    var ip by mutableStateOf(prefs.ip)
    var wsOn by mutableStateOf(false)
    var smsOn by mutableStateOf(prefs.smsOn)
    var smsNums by mutableStateOf(prefs.smsNums)
    var smsMin by mutableStateOf(prefs.smsMin)
    var smsCool by mutableStateOf(prefs.smsCool)
    var smsLog by mutableStateOf("")
    val raw = mutableStateListOf<String>()
    var wzOn by mutableStateOf(false)
    var wzStep by mutableStateOf(0)
    var wzRecording by mutableStateOf(false)
    var wzSug by mutableStateOf<Cfg?>(null)

    // ---- internals ----
    private var lastLvl = 0
    private var acked = false
    private var prevRain = false
    private var predWarn = false
    private var calBuf: ArrayList<Reading>? = null
    private var wzBuf: ArrayList<Reading>? = null
    private val wzRes = ArrayList<Reading>()
    private var lastRx = 0L
    private var faulty = false
    private var flashState: String? = null
    private var flashUntil = 0L
    private var smsLast = 0L
    private var smsLastLvl = 0
    private var fails = 0
    private var lockUntil = 0L
    private var ws: WebSocket? = null
    private var wsOk = false
    private var demoJob: Job? = null
    private var tick = 0
    private val sayHide = Runnable { dripSayText = "" }

    init {
        incidents.addAll(prefs.loadIncidents())
        val saved = prefs.role
        when {
            saved.isEmpty() -> { role = "consumer"; roleChosen = false }
            saved == "dev" -> { role = "consumer"; roleChosen = false; devAsk = true }   // developer mode asks again on every start
            Roles.NAME.containsKey(saved) -> { role = saved; roleChosen = true }
            else -> { role = "consumer"; roleChosen = true }
        }
        viewModelScope.launch {
            while (isActive) { delay(1000); secondTick() }
        }
    }

    // ---- modes ----
    fun chooseRole(r: String) { role = r; prefs.role = r; roleChosen = true; devAsk = false; devMsg = ""; chooserCancel = false }
    fun openChooser(askDev: Boolean = false) { roleChosen = false; devAsk = askDev; devMsg = ""; chooserCancel = true }
    fun cancelChooser() { roleChosen = true; devAsk = false; chooserCancel = false }

    fun tryDev(pw: String) {
        val now = SystemClock.elapsedRealtime()
        if (now < lockUntil) { devMsg = "Too many attempts. Wait a few seconds."; return }
        val expected = prefs.devPw.ifEmpty { Prefs.DEFAULT_HASH }
        if (Prefs.hash(pw) == expected) { fails = 0; chooseRole("dev") }
        else {
            fails++; devMsg = "Wrong password."
            if (fails >= 5) { lockUntil = now + 30000; fails = 0 }
        }
    }

    fun changeDevPw(v: String): String {
        if (v.length < 4) return "At least 4 characters."
        prefs.devPw = Prefs.hash(v); return "Password changed."
    }
    fun resetDevPw(): String { prefs.devPw = ""; return "Password reset to 1234." }

    // ---- settings ----
    fun setCfg(c: Cfg) { cfg = c; prefs.cfg = c }
    fun resetCfg() = setCfg(Cfg())
    fun setMuted(m: Boolean) { mute = m; prefs.mute = m }
    fun setVolume(v: Float) { vol = v; prefs.vol = v }
    fun setVibrateOn(v: Boolean) { vibrate = v; prefs.vibrate = v }
    fun setDripOn(v: Boolean) { dripOn = v; prefs.drip = v }
    fun setAccent(a: String) { accent = a; prefs.accent = a }
    fun setModeTo(m: String) { mode = m; prefs.mode = m }
    fun setCalmOn(c: Boolean) { calm = c; prefs.calm = c }
    fun renameNode(n: String) { val t = n.trim().ifEmpty { "Drain 1" }; node = t; prefs.node = t }
    fun sndOn(k: String) = prefs.sndOn(k).also { sndVer }
    fun setSndOn(k: String, v: Boolean) { prefs.setSnd(k, v); sndVer++ }
    fun toggleRecording() { if (recording) recording = false else { recRows.clear(); recCount = 0; recording = true } }
    fun recCsv(label: String): String = (listOf("time,label,flow,dist,turb,rain,condition") + recRows.map { "$it".replace("{L}", label) }).joinToString("\n")
    fun saveSms() { prefs.smsOn = smsOn; prefs.smsNums = smsNums; prefs.smsMin = smsMin; prefs.smsCool = smsCool }
    fun clearIncidents() { incidents.clear(); prefs.saveIncidents(incidents) }

    // ---- Wi-Fi link (WebSocket, port 81) ----
    fun connectWs(address: String) {
        val a = address.trim()
        if (a.isEmpty()) { msg = "Enter the board address first."; return }
        stopAll()
        ip = a; prefs.ip = a; wsOn = true
        openWs()
    }

    private fun openWs() {
        val req = try { Request.Builder().url("ws://$ip:81").build() } catch (e: Exception) {
            msg = "That address is not valid."; wsOn = false; return
        }
        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                main.post { if (webSocket === ws) { wsOk = true; lastRx = SystemClock.elapsedRealtime(); setConn(true, "Connected (Wi-Fi)"); msg = "Connected over Wi-Fi." } }
            }
            override fun onMessage(webSocket: WebSocket, text: String) {
                main.post { text.split("\n").forEach { handleLine(it.trim()) } }
            }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = lost(webSocket, false)
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) = lost(webSocket, true)
        }
        ws = http.newWebSocket(req, listener)
    }

    private fun lost(w: WebSocket, failed: Boolean) {
        main.post {
            if (w !== ws) return@post
            wsOk = false
            setConn(false, if (wsOn) "Not connected, retrying…" else "Not connected")
            if (failed) msg = "Cannot reach the board. Check the address and that this phone is on the same Wi-Fi."
            if (wsOn) main.postDelayed({ if (wsOn && w === ws) openWs() }, 3000)
        }
    }

    fun stopAll() {
        stopDemo()
        wsOn = false
        val w = ws; ws = null; wsOk = false
        try { w?.close(1000, null) } catch (e: Exception) { }
        setConn(false, "Not connected")
    }

    private fun setConn(ok: Boolean, label: String) {
        if (ok != connected) {
            sound.play(if (ok) "connect" else "disconnect")
            if (ok) dripFlash("wave", 2200, "Board connected.")
        }
        connected = ok; connLabel = label
    }

    fun send(o: String): Boolean {
        val w = ws
        if (w != null && wsOk) return w.send(o + "\n")
        return false
    }

    fun sendConsole(cmd: String) {
        if (cmd.isBlank()) return
        if (send(cmd)) addRaw("> $cmd") else msg = "Connect the board first."
    }

    private fun addRaw(l: String) { raw.add(l); while (raw.size > 200) raw.removeAt(0) }

    private fun handleLine(l: String) {
        if (l.isEmpty()) return
        addRaw(l)
        if (l[0] != '{') return
        val d = try { JSONObject(l) } catch (e: Exception) { return }
        if (d.has("flow")) {
            onData(Reading(d.optDouble("flow", 0.0), d.optDouble("dist", 0.0), d.optDouble("turb", 0.0), d.optInt("rain", 0) != 0 || d.optBoolean("rain", false)))
        }
    }

    // ---- demo ----
    fun toggleDemo() { if (demo) stopDemo() else startDemo() }

    fun startDemo() {
        stopAll()
        demo = true; tick = 0; scen = "normal"; hist.clear(); lastLvl = 0; connLabel = "Demo data"
        demoJob = viewModelScope.launch {
            while (isActive) {
                delay(1000)
                tick++
                val p = SCEN[if (calBuf != null || wzBuf != null) "normal" else scen] ?: SCEN["normal"]!!
                fun n() = Math.random() - 0.5
                onData(Reading(p[0] + n() * 0.2, p[1] + n() * 0.2, p[2] + n() * 30, p[3] > 0.5))
                if (tick == 2 && base == null) startBaseline()
            }
        }
    }

    fun stopDemo() {
        if (demo) { demo = false; demoJob?.cancel(); demoJob = null; connLabel = "Not connected" }
    }

    fun setScenario(k: String) { scen = k; msg = "Demo scenario: " + (SCEN_NAMES[k] ?: k) }

    // ---- calibration ----
    fun startBaseline() {
        if (!connected && !demo) { msg = "Connect the board or start demo mode first."; return }
        calBuf = ArrayList(); msg = "Setting baseline… keep normal flow."
    }

    private fun finishBaseline(rows: List<Reading>) {
        val b = Core.baseFrom(rows)
        base = b; prefs.base = b
        sound.play("baseline"); dripFlash("cheer", 2500, "Baseline saved!")
    }

    fun wizardStart() { wzOn = true; wzStep = 0; wzRes.clear(); wzBuf = null; wzRecording = false; wzSug = null }

    fun wizardRecord() {
        if (!connected && !demo) { msg = "Connect the board or start demo mode first."; return }
        wzBuf = ArrayList(); wzRecording = true
    }

    fun wizardApply() { wzSug?.let { setCfg(it); msg = "Suggested thresholds applied." } }

    private fun wizardData(buf: ArrayList<Reading>) {
        if (buf.size < 10) return
        wzRes.add(Reading(buf.map { it.flow }.average(), buf.map { it.dist }.average(), buf.map { it.turb }.average(), buf.count { it.rain } * 2 > buf.size))
        if (wzStep == 0) finishBaseline(buf)
        wzBuf = null; wzRecording = false; wzStep++
        if (wzStep >= WZ_STEPS.size && wzRes.size >= 3) {
            val n = wzRes[0]; val p = wzRes[1]; val hv = wzRes[2]
            wzSug = cfg.copy(
                dropWarn = maxOf(10.0, ((1 - p.flow / n.flow) * 50).roundToInt().toDouble()),
                dropBlock = maxOf(30.0, ((1 - hv.flow / n.flow) * 70).roundToInt().toDouble()),
                rise = maxOf(0.5, ((n.dist - p.dist) * 5).roundToInt() / 10.0)
            )
        }
        sound.play("baseline"); dripFlash("cheer", 2500, "Step saved!")
    }

    // ---- incoming reading ----
    private fun onData(d: Reading) {
        lastRx = SystemClock.elapsedRealtime()
        val cb = calBuf
        if (cb != null) {
            cb.add(d); msg = "Setting baseline… ${cb.size}/10"
            if (cb.size >= 10) { finishBaseline(cb); calBuf = null; msg = "Baseline saved. Keep the valve fully open." }
        }
        val wb = wzBuf
        if (wb != null) { wb.add(d); wizardData(wb) }

        val h = Core.health(d, hist, base)
        val e = Core.evaluate(d, h.bad, base, cfg)
        val level = Core.LEVELS[e.lvl]
        if (d.rain && !prevRain) { sound.play("rain"); say("Rain detected.") }
        prevRain = d.rain; dripRain = d.rain

        val eta = Core.predictEta(hist, cfg.over)
        var pred = ""
        if (eta != null && eta < 1800) {
            pred = "Prediction: overflow in about " + (if (eta < 90) "${eta.roundToInt()} s" else String.format(Locale.US, "%.1f min", eta / 60)) + " at the current rate"
            if (eta < 180 && !predWarn) { predWarn = true; sound.play("predict"); say("Overflow predicted in about ${maxOf(1, (eta / 60).roundToInt())} min.") }
        } else predWarn = false

        if (e.lvl > lastLvl) {
            incidents.add(0, Incident(SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date()), level.name, e.cause,
                e.ev.joinToString("; "), level.sev, e.conf, e.lvl, level.color))
            while (incidents.size > 200) incidents.removeAt(incidents.size - 1)
            prefs.saveIncidents(incidents)
            acked = false
            sound.play(listOf("", "possible", "warning", "risk", "overflow")[e.lvl])
            if (e.lvl >= 3) sound.buzz()
            maybeSms(e, level)
        } else if (e.lvl == 0 && lastLvl > 0) {
            sound.play("normal"); smsLastLvl = 0; dripFlash("cheer", 2500, "Back to normal!")
        }
        lastLvl = e.lvl
        banner = if (e.lvl >= 3 && !acked) level.name + ": " + e.cause else ""
        if (recording) {
            recRows.add(SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).format(Date()) + ",{L}," + d.flow + "," + d.dist + "," + d.turb + "," + (if (d.rain) 1 else 0) + "," + level.name)
            recCount = recRows.size
        }
        hist.add(Sample(System.currentTimeMillis(), d.flow, d.dist))
        while (hist.size > 900) hist.removeAt(0)
        histVer++
        faulty = h.bad || h.issues.any { it.contains("not changing") || it.contains("frozen") || it.contains("limit") }
        snap = Snap(d, e, level, h.issues, pred)
        dripSync()
    }

    fun acknowledge() { acked = true; banner = "" }

    // ---- Drip ----
    fun say(text: String, ms: Long = 4500) {
        dripSayText = text
        main.removeCallbacks(sayHide); main.postDelayed(sayHide, ms)
    }

    fun dripFlash(state: String, ms: Long, text: String) {
        flashState = state; flashUntil = SystemClock.elapsedRealtime() + ms
        dripSync()
        if (text.isNotEmpty()) say(text)
        main.postDelayed({ dripSync() }, ms + 50)
    }

    private fun baseState(): String {
        val live = SystemClock.elapsedRealtime() - lastRx <= 5000
        if (!demo && (!connected || !live)) return "sleep"
        if (faulty) return "dizzy"
        return when {
            lastLvl >= 4 -> "panic"
            lastLvl == 3 -> "alarmed"
            lastLvl == 2 -> "worried"
            lastLvl == 1 -> "curious"
            calBuf != null || wzBuf != null -> "think"
            else -> "idle"
        }
    }

    private fun dripSync() {
        val now = SystemClock.elapsedRealtime()
        val n = if (now < flashUntil) flashState ?: baseState() else baseState()
        if (n != dripState) {
            dripState = n
            if (now >= flashUntil) DripChat.line(n)?.let { say(it) }
        }
    }

    fun dripTap() {
        say(DripChat.reply("status", chatCtx()).text, 7000)
        dripFlash("happy", 1400, "")
    }

    fun chatCtx(): DripChat.Ctx {
        val s = snap
        val live = s != null && (demo || (connected && SystemClock.elapsedRealtime() - lastRx < 30000))
        return DripChat.Ctx(lastLvl, live, if (s != null) "$node: ${s.level.icon} ${s.level.name}" else "", s?.e?.cause ?: "",
            s?.e?.ev?.joinToString("; ") ?: "", s?.pred ?: "")
    }

    fun act(a: String?) {
        when (a) {
            "baseline" -> startBaseline()
            "demo" -> toggleDemo()
            "mute" -> setMuted(true)
            "unmute" -> setMuted(false)
            "ack" -> acknowledge()
        }
    }

    private fun secondTick() {
        val now = SystemClock.elapsedRealtime()
        dripSync()
        if (connected && lastRx != 0L && now - lastRx > 5000) msg = "No data for ${(now - lastRx) / 1000} s: check the board and Wi-Fi"
        if (lastLvl >= 3 && !acked) sound.play(if (lastLvl == 4) "overflow" else "risk", 3000)
    }

    // ---- SMS through the board ----
    private fun numbers() = smsNums.split(",").mapNotNull { Core.normNum(it.trim()) }

    fun smsSend(text: String): String {
        val n = numbers()
        if (n.isEmpty()) return "No valid mobile number"
        if (!send(JSONObject().put("cmd", "sms").put("to", n[0]).put("msg", text).toString())) return "Not sent: board not connected"
        n.drop(1).forEach { send(JSONObject().put("cmd", "sms").put("to", it).put("msg", text).toString()) }
        return "Sent to " + n.joinToString(", ") + " via the board"
    }

    fun testSms() { smsLog = smsSend("FlowBeacon: test message from the app.") }

    private fun maybeSms(e: Eval, level: Level) {
        if (!smsOn || e.lvl < smsMin) return
        val now = SystemClock.elapsedRealtime()
        if (smsLast != 0L && now - smsLast < smsCool * 60000L && e.lvl <= smsLastLvl) return
        val m = ("FlowBeacon: ${level.name}. ${e.cause}. ${e.ev.joinToString(", ")}. " +
            SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.US).format(Date())).filter { it.code in 32..126 }.take(160)
        val r = smsSend(m)
        smsLog = r
        if (r.startsWith("Sent")) { smsLast = now; smsLastLvl = e.lvl }
    }

    fun csv(): String {
        fun q(s: String) = "\"" + s.replace("\"", "\"\"") + "\""
        return (listOf("Time,Condition,Likely cause,Sensor evidence,Severity,Confidence %") +
            incidents.map { listOf(it.time, it.cond, it.cause, it.ev, it.sev, it.conf.toString()).joinToString(",") { c -> q(c) } }).joinToString("\n")
    }

    override fun onCleared() {
        stopAll()
        try { http.dispatcher.executorService.shutdown() } catch (e: Exception) { }
        super.onCleared()
    }

    companion object {
        val SCEN = mapOf(
            "normal" to listOf(4.2, 12.5, 850.0, 0.0), "partial" to listOf(2.0, 11.0, 1150.0, 0.0),
            "rain" to listOf(4.1, 10.8, 860.0, 1.0), "both" to listOf(1.6, 8.5, 1200.0, 1.0), "over" to listOf(0.9, 1.8, 1300.0, 1.0)
        )
        val SCEN_NAMES = mapOf("normal" to "Normal", "partial" to "Partial blockage", "rain" to "Rain", "both" to "Blockage + rain", "over" to "Overflow")
    }
}
