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
import kotlinx.coroutines.Dispatchers
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

class Snap(val d: Reading, val e: Eval, val level: Level, val issues: List<String>, val pred: String, val ml: String = "")

class Profile(val name: String, val cfg: Cfg, val base: Base?)

object Roles {
    val ALL = listOf("overview", "model", "incidents", "connect", "history", "calib", "drip", "settings", "console", "map")
    val NAME = mapOf("consumer" to "Consumer", "team" to "Maintenance team", "dev" to "Developer")
    val DESC = mapOf(
        "consumer" to "See drain status, live readings, the drain model and history. No controls.",
        "team" to "Full operational control: incidents, city map and dispatch, board connection and calibration.",
        "dev" to "Full control of everything, including the firmware console. Can switch to any mode. Password required."
    )
    fun tabs(role: String): List<String> = when (role) {
        "consumer" -> listOf("overview", "model", "history", "drip", "settings")
        "team" -> ALL.filter { it != "console" }
        else -> ALL
    }
}

val WZ_STEPS = listOf("Normal flow, valve fully open", "Partial valve, about half closed", "Valve mostly closed", "Wet the rain plate")

/** All app state and logic: readings, conditions, incidents, Wi-Fi link, demo mode and Drip's mood. */
class AppVm(app: Application) : AndroidViewModel(app) {
    val prefs = Prefs(app)
    val sound = Sound(app, prefs)
    val history = HistoryDb(app)
    val city = CityBook(prefs)
    private val nodeMap = LinkedHashMap<String, NodeLive>()
    var appVisible = false
    private var lastRxWall = 0L
    private var secCount = 0
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
    var nodesVer by mutableStateOf(0)
    var cityVer by mutableStateOf(0)
    var lang by mutableStateOf(prefs.lang)
    var zoom by mutableStateOf(prefs.zoom)
    var notifyOn by mutableStateOf(prefs.notify)
    var bgOn by mutableStateOf(prefs.bg)
    var updOn by mutableStateOf(prefs.upd)
    var quietOn by mutableStateOf(prefs.quietOn)
    var quietFrom by mutableStateOf(prefs.quietFrom)
    var quietTo by mutableStateOf(prefs.quietTo)
    var quietSms by mutableStateOf(prefs.quietSms)
    var useModel by mutableStateOf(prefs.useModel)
    var model by mutableStateOf(NbModel.fromJson(prefs.modelJson))
    var trainRows by mutableStateOf<List<CsvRow>>(emptyList())
    var trainMsg by mutableStateOf("")
    var playRows by mutableStateOf<List<CsvRow>>(emptyList())
    var replaying by mutableStateOf(false)
    var replayMsg by mutableStateOf("")
    val profiles = mutableStateListOf<Profile>()
    var upd by mutableStateOf<UpdateInfo?>(null)
    var updMsg by mutableStateOf("")
    var usbLabels by mutableStateOf<List<String>>(emptyList())
    private var usbDrivers: List<com.hoho.android.usbserial.driver.UsbSerialDriver> = emptyList()
    private var usb: UsbLink? = null
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
        loadProfiles()
        sound.quiet = { inQuiet() }
        history.prune()
        if (prefs.upd) main.postDelayed({ checkUpdates(false) }, 6000)
        viewModelScope.launch {
            while (isActive) { delay(1000); secondTick() }
        }
    }

    // ---- quiet hours, language, text size, notifications ----
    fun inQuiet(): Boolean {
        if (!quietOn) return false
        fun m(x: String): Int { val p = x.split(":"); return (p.getOrNull(0)?.toIntOrNull() ?: 0) * 60 + (p.getOrNull(1)?.toIntOrNull() ?: 0) }
        val c = java.util.Calendar.getInstance()
        val now = c.get(java.util.Calendar.HOUR_OF_DAY) * 60 + c.get(java.util.Calendar.MINUTE)
        val a = m(quietFrom); val b = m(quietTo)
        return if (a <= b) now in a until b else (now >= a || now < b)
    }

    fun setLanguage(l: String) { lang = l; prefs.lang = l }
    fun setZoomTo(z: Float) { zoom = z; prefs.zoom = z }
    fun setNotifyOn(v: Boolean) { notifyOn = v; prefs.notify = v }
    fun setBgOn(v: Boolean) { bgOn = v; prefs.bg = v; syncService() }
    fun setUpdOn(v: Boolean) { updOn = v; prefs.upd = v }
    fun setQuietOn(v: Boolean) { quietOn = v; prefs.quietOn = v }
    fun setQuietFrom(v: String) { quietFrom = v; prefs.quietFrom = v }
    fun setQuietTo(v: String) { quietTo = v; prefs.quietTo = v }
    fun setQuietSms(v: Int) { quietSms = v; prefs.quietSms = v }
    fun setUseModel(v: Boolean) { useModel = v; prefs.useModel = v }

    private fun notifyLevel(lvl: Int, name: String, cause: String, node: String) {
        if (!notifyOn || lvl < 2 || (inQuiet() && lvl < 3) || appVisible) return      // the app itself already shows a banner and plays a sound
        Notifier.alert(getApplication(), "FlowBeacon: " + Tamil.trans(name, lang), node + " · " + Tamil.trans(cause, lang))
    }

    /** Keeps the app alive in the background while a board is connected (a foreground service with a small notification). */
    fun syncService() {
        val app = getApplication<Application>()
        if (bgOn && connected && !demo) AlertService.start(app, node + ": " + (snap?.level?.name ?: "waiting for data")) else AlertService.stop(app)
    }

    // ---- calibration profiles ----
    private fun loadProfiles() {
        try {
            val a = org.json.JSONArray(prefs.profilesJson)
            for (i in 0 until a.length()) {
                val o = a.getJSONObject(i); val c = o.getJSONObject("cfg")
                val b = o.optJSONObject("base")
                profiles.add(Profile(o.getString("name"), Cfg(c.getDouble("dropWarn"), c.getDouble("dropBlock"), c.getDouble("rise"), c.getDouble("risk"), c.getDouble("over"), c.getDouble("turb")),
                    if (b != null) Base(b.getDouble("flow"), b.getDouble("dist"), b.getDouble("turb"), b.getDouble("sf"), b.getDouble("sd"), b.getDouble("st")) else null))
            }
        } catch (e: Exception) { }
    }

    private fun saveProfiles() {
        val a = org.json.JSONArray()
        profiles.forEach { p ->
            val o = JSONObject().put("name", p.name).put("cfg", JSONObject().put("dropWarn", p.cfg.dropWarn).put("dropBlock", p.cfg.dropBlock)
                .put("rise", p.cfg.rise).put("risk", p.cfg.risk).put("over", p.cfg.over).put("turb", p.cfg.turb))
            p.base?.let { b -> o.put("base", JSONObject().put("flow", b.flow).put("dist", b.dist).put("turb", b.turb).put("sf", b.sf).put("sd", b.sd).put("st", b.st)) }
            a.put(o)
        }
        prefs.profilesJson = a.toString()
    }

    fun profileSave(name: String) { if (name.isBlank()) return; profiles.add(Profile(name.trim(), cfg, base)); saveProfiles() }
    fun profileApply(i: Int) { profiles.getOrNull(i)?.let { p -> updateCfg(p.cfg); p.base?.let { base = it; prefs.base = it } } }
    fun profileDelete(i: Int) { if (i in profiles.indices) { profiles.removeAt(i); saveProfiles() } }

    // ---- learn from recordings and replay ----
    fun loadTraining(rows: List<CsvRow>) { trainRows = rows; trainMsg = "${rows.size} readings loaded." }

    fun trainModel() {
        val b = base
        if (b == null) { trainMsg = "Set the baseline first."; return }
        if (trainRows.isEmpty()) { trainMsg = "No readings loaded."; return }
        val data = trainRows.map { Labelled(it.label, Ml.features(it.r, b)) }
        val m = Ml.train(data, b)
        model = m; prefs.modelJson = m.toJson()
        trainMsg = "Trained on ${data.size} readings, labels: ${m.labels.joinToString(", ")}. Accuracy on these files: ${(Ml.accuracy(m, data) * 100).roundToInt()}%."
    }

    private fun mlShow(d: Reading): String {
        val m = model; val b = base
        if (!useModel || m == null || b == null) return ""
        val p = Ml.predict(m, Ml.features(d, b))
        return "Learned model: ${p.first} (${(p.second * 100).roundToInt()}%)"
    }

    fun startReplay(rows: List<CsvRow>, speed: Int) {
        if (rows.isEmpty()) return
        stopAll()
        if (base == null && rows.size >= 10) { val b = Core.baseFrom(rows.take(10).map { it.r }); base = b; prefs.base = b }
        hist.clear(); lastLvl = 0; replaying = true; connLabel = "Replay"; replayMsg = "Playing ${rows.size} readings…"
        demoJob = viewModelScope.launch {
            var i = 0
            while (isActive && i < rows.size) { onData(rows[i++].r); delay(maxOf(40L, 1000L / maxOf(1, speed))) }
            replaying = false; connLabel = "Not connected"; replayMsg = "Replay finished."
        }
    }

    fun stopReplay() {
        if (!replaying) return
        demoJob?.cancel(); demoJob = null; replaying = false; connLabel = "Not connected"; replayMsg = ""
    }

    // ---- update check ----
    fun checkUpdates(manual: Boolean) {
        if (manual) updMsg = "Checking…"
        viewModelScope.launch(Dispatchers.IO) {
            val r = Updater.check()
            main.post {
                if (r.error.isNotEmpty()) { if (manual) updMsg = "Could not check: " + r.error }
                else if (r.newer) { upd = r; if (manual) updMsg = "Version ${r.latest} is available." }
                else if (manual) updMsg = "You have the latest version (${r.current})."
            }
        }
    }

    // ---- other drains and the city map ----
    fun liveNodes(): List<NodeLive> {
        val out = ArrayList<NodeLive>()
        val s = snap
        if (s != null) out.add(NodeLive("drain-1", node).also { it.lvl = lastLvl; it.rx = lastRxWall; it.last = s.d; it.base = base })
        out.addAll(nodeMap.values)
        return out
    }

    /** Other drains as (name, level); reads nodesVer so screens refresh. */
    fun otherNames(): List<Pair<String, Int>> { val v = nodesVer; return if (v < 0) emptyList() else nodeMap.values.map { it.name to it.lvl } }

    fun nodeList(): List<Pair<String, String>> { val v = nodesVer; return if (v < 0) emptyList() else listOf("drain-1" to node) + nodeMap.values.map { it.id to it.name } }

    private fun trackCity(n: NodeLive) {
        val st = city.states(listOf(n)).firstOrNull { it.id == n.id } ?: return
        if (city.track(st)) { city.save(); cityVer++ }
    }

    private fun otherNode(id: String, r: Reading) {
        val n = nodeMap.getOrPut(id) {
            NodeLive(id, CityBook.DEMO[id]?.name ?: id).also { if (id.startsWith("demo-")) it.base = Base(4.2, 12.5, 850.0, 0.2, 0.2, 30.0) }
        }
        n.rx = System.currentTimeMillis(); n.last = r
        if (n.base == null) { n.buf.add(r); if (n.buf.size >= 10) n.base = Core.baseFrom(n.buf) }      // the first 10 readings of a new drain become its baseline
        val h = Core.health(r, n.hist, n.base)
        val e = Core.evaluate(r, h.bad, n.base, cfg)
        if (e.lvl > n.lvl) notifyLevel(e.lvl, Core.LEVELS[e.lvl].name, e.cause, n.name)
        n.lvl = e.lvl
        n.hist.add(Sample(System.currentTimeMillis(), r.flow, r.dist)); while (n.hist.size > 900) n.hist.removeAt(0)
        history.add(id, r, e.lvl)
        trackCity(n)
        nodesVer++
    }

    // ---- USB serial ----
    fun refreshUsb() {
        val u = usb ?: UsbLink(getApplication(), { line -> main.post { handleLine(line) } }, { ok, label ->
            main.post { setConn(ok, if (ok) label else "Not connected"); msg = if (ok) "Reading from the ESP32-S3…" else label }
        }).also { usb = it }
        usbDrivers = u.drivers()
        usbLabels = usbDrivers.map { d -> (d.device.productName ?: "USB device") + " (" + Integer.toHexString(d.device.vendorId) + ":" + Integer.toHexString(d.device.productId) + ")" }
        if (usbDrivers.isEmpty()) msg = "No USB board found. Plug the ESP32-S3 into the phone with a USB OTG cable."
    }

    fun connectUsb(i: Int) {
        val d = usbDrivers.getOrNull(i) ?: return
        stopAll()
        msg = "Asking for USB permission…"
        (usb ?: return).connect(d)
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
    fun updateCfg(c: Cfg) { cfg = c; prefs.cfg = c }
    fun resetCfg() = updateCfg(Cfg())
    fun setMuted(m: Boolean) { mute = m; prefs.mute = m }
    fun setVolume(v: Float) { vol = v; prefs.vol = v }
    fun setVibrateOn(v: Boolean) { vibrate = v; prefs.vibrate = v }
    fun updateDripOn(v: Boolean) { dripOn = v; prefs.drip = v }
    fun updateAccent(a: String) { accent = a; prefs.accent = a }
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
        stopReplay()
        try { usb?.close() } catch (e: Exception) { }
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
        syncService()
    }

    fun send(o: String): Boolean {
        val u = usb
        if (u != null && u.isOpen) return u.write(o + "\n")
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
            val r = Reading(d.optDouble("flow", 0.0), d.optDouble("dist", 0.0), d.optDouble("turb", 0.0), d.optInt("rain", 0) != 0 || d.optBoolean("rain", false))
            val id = d.optString("node", "drain-1").ifEmpty { "drain-1" }
            if (id != "drain-1") otherNode(id, r) else onData(r)
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
                DEMO_EXTRA.forEach { x -> otherNode(x.first, Reading(x.second[0] + n() * 0.2, x.second[1] + n() * 0.2, x.second[2] + n() * 30, false)) }
                if (tick == 2 && base == null) startBaseline()
            }
        }
    }

    fun stopDemo() {
        if (demo) {
            demo = false; demoJob?.cancel(); demoJob = null; connLabel = "Not connected"
            nodeMap.keys.removeAll { it.startsWith("demo-") }; nodesVer++
        }
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

    fun wizardApply() { wzSug?.let { updateCfg(it); msg = "Suggested thresholds applied." } }

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
        lastRxWall = System.currentTimeMillis()
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
            notifyLevel(e.lvl, level.name, e.cause, node)
            if (bgOn && connected) Notifier.updateMonitor(getApplication(), node + ": " + level.name)
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
        history.add("drain-1", d, e.lvl)
        hist.add(Sample(System.currentTimeMillis(), d.flow, d.dist))
        while (hist.size > 900) hist.removeAt(0)
        histVer++
        faulty = h.bad || h.issues.any { it.contains("not changing") || it.contains("frozen") || it.contains("limit") }
        snap = Snap(d, e, level, h.issues, pred, mlShow(d))
        trackCity(NodeLive("drain-1", node).also { it.lvl = e.lvl; it.rx = lastRxWall; it.last = d; it.base = base })
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
        if (!demo && !replaying && (!connected || !live)) return "sleep"
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
        secCount++
        if (secCount % 60 == 0) history.flushAll(60000)
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
        val floor = maxOf(smsMin, if (inQuiet()) quietSms else 0)
        if (!smsOn || e.lvl < floor) return
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
        sound.release()
        history.flushAll()
        try { http.dispatcher.executorService.shutdown() } catch (e: Exception) { }
        super.onCleared()
    }

    companion object {
        val DEMO_EXTRA = listOf("demo-2" to listOf(4.1, 12.4, 870.0), "demo-3" to listOf(2.2, 10.6, 1100.0))
        val SCEN = mapOf(
            "normal" to listOf(4.2, 12.5, 850.0, 0.0), "partial" to listOf(2.0, 11.0, 1150.0, 0.0),
            "rain" to listOf(4.1, 10.8, 860.0, 1.0), "both" to listOf(1.6, 8.5, 1200.0, 1.0), "over" to listOf(0.9, 1.8, 1300.0, 1.0)
        )
        val SCEN_NAMES = mapOf("normal" to "Normal", "partial" to "Partial blockage", "rain" to "Rain", "both" to "Blockage + rain", "over" to "Overflow")
    }
}
