package com.techminds.flowbeacon

import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import kotlin.math.cos
import kotlin.math.sin

class Device(var name: String, var ward: String, var zone: String, var lat: Double, var lng: Double, var placed: Boolean)
class LogE(val t: Long, val m: String)
class Inc(val id: String, val dev: String, var level: Int, var max: Int, val start: Long, var status: String, var team: String, val log: MutableList<LogE>) {
    var end = 0L; var by = ""; var assigned = 0L
}
class NodeLive(val id: String, var name: String) {
    var lvl = 0; var rx = 0L; var last: Reading? = null; var base: Base? = null
    val hist = ArrayList<Sample>(); val buf = ArrayList<Reading>()
}
class DevState(val id: String, val dv: Device, val lvl: Int, val status: String, val online: Boolean, val last: Reading?, val base: Base?, val name: String)

/** City drainage map data and dispatch workflow (port of src/map.js; the map itself is drawn on a canvas, no tiles needed). */
class CityBook(private val prefs: Prefs) {
    val devices = LinkedHashMap<String, Device>()
    val teams = ArrayList<String>()
    val incidents = ArrayList<Inc>()
    val hide = HashSet<String>()
    var officer = ""
    var pin: String? = null
    var salt = ""
    var unlocked = false
    private val normalCount = HashMap<String, Int>()

    init { load() }

    val locked: Boolean get() = pin != null && !unlocked

    // ---- saving (demo drains are never saved) ----
    private fun load() {
        teams.addAll(listOf("Team A", "Team B", "Team C"))
        val s = prefs.mapJson
        if (s.isEmpty()) return
        try {
            val o = JSONObject(s)
            teams.clear(); o.optJSONArray("teams")?.let { a -> for (i in 0 until a.length()) teams.add(a.getString(i)) }
            officer = o.optString("officer", ""); salt = o.optString("salt", "")
            pin = if (o.has("pin") && !o.isNull("pin")) o.getString("pin") else null
            o.optJSONArray("hide")?.let { a -> for (i in 0 until a.length()) hide.add(a.getString(i)) }
            o.optJSONObject("devices")?.let { d -> d.keys().forEach { k -> val v = d.getJSONObject(k)
                devices[k] = Device(v.optString("name"), v.optString("ward"), v.optString("zone"), v.getDouble("lat"), v.getDouble("lng"), v.optBoolean("placed")) } }
            o.optJSONArray("incidents")?.let { a -> for (i in 0 until a.length()) {
                val v = a.getJSONObject(i)
                val log = ArrayList<LogE>(); v.optJSONArray("log")?.let { l -> for (j in 0 until l.length()) log.add(LogE(l.getJSONObject(j).getLong("t"), l.getJSONObject(j).getString("m"))) }
                incidents.add(Inc(v.getString("id"), v.getString("dev"), v.getInt("level"), v.getInt("max"), v.getLong("start"), v.getString("status"), v.optString("team"), log).also {
                    it.end = v.optLong("end"); it.by = v.optString("by"); it.assigned = v.optLong("assigned") })
            } }
        } catch (e: Exception) { }
    }

    fun save() {
        try {
            val d = JSONObject()
            devices.filterKeys { !it.startsWith("demo-") }.forEach { (k, v) ->
                d.put(k, JSONObject().put("name", v.name).put("ward", v.ward).put("zone", v.zone).put("lat", v.lat).put("lng", v.lng).put("placed", v.placed))
            }
            val inc = JSONArray()
            incidents.filter { !it.dev.startsWith("demo-") }.forEach { i ->
                inc.put(JSONObject().put("id", i.id).put("dev", i.dev).put("level", i.level).put("max", i.max).put("start", i.start).put("status", i.status)
                    .put("team", i.team).put("end", i.end).put("by", i.by).put("assigned", i.assigned)
                    .put("log", JSONArray(i.log.map { JSONObject().put("t", it.t).put("m", it.m) })))
            }
            prefs.mapJson = JSONObject().put("devices", d).put("incidents", inc).put("teams", JSONArray(teams)).put("hide", JSONArray(hide.toList()))
                .put("officer", officer).put("salt", salt).put("pin", pin ?: JSONObject.NULL).toString()
        } catch (e: Exception) { }
    }

    // ---- devices ----
    private fun autoPlace(id: String): Device {
        DEMO[id]?.let { return Device(it.name, it.ward, it.zone, it.lat, it.lng, true) }
        var h = 0L
        for (ch in id) h = (h * 31 + ch.code) and 0xFFFFFFFFL
        val a = Math.toRadians((h % 360).toDouble())
        val r = 0.004 + ((h shr 9) % 100) / 100.0 * 0.02
        return Device("", "", "", Math.round((CENTER_LAT + sin(a) * r) * 100000) / 100000.0, Math.round((CENTER_LNG + cos(a) * r) * 100000) / 100000.0, false)
    }

    fun ensure(id: String): Device? {
        if (id in hide) return null
        return devices.getOrPut(id) { autoPlace(id) }
    }

    fun states(live: List<NodeLive>, now: Long = System.currentTimeMillis()): List<DevState> {
        val by = live.associateBy { it.id }
        by.keys.forEach { ensure(it) }
        return devices.filterKeys { it !in hide }.map { (id, dv) ->
            val n = by[id]
            val online = n != null && n.rx != 0L && now - n.rx < STALE_MS
            val lvl = if (n != null && online) n.lvl else 0
            val status = if (!online) "offline" else listOf("normal", "possible", "blockage", "overflow", "overflow")[lvl]
            DevState(id, dv, lvl, status, online, n?.last, n?.base, n?.name ?: id)
        }
    }

    fun label(s: DevState) = s.dv.name.ifEmpty { if (s.name != s.id) s.name else s.id }

    fun addDevice(id: String): String? {
        val t = id.trim().take(40)
        if (t.isEmpty()) return null
        hide.remove(t)
        devices.getOrPut(t) { autoPlace(t) }
        return t
    }

    fun editDevice(id: String, name: String, ward: String, zone: String, lat: Double?, lng: Double?): Boolean {
        val dv = devices[id] ?: return false
        if (lat == null || lng == null || lat !in -90.0..90.0 || lng !in -180.0..180.0) return false
        dv.name = name.trim(); dv.ward = ward.trim(); dv.zone = zone.trim(); dv.lat = lat; dv.lng = lng; dv.placed = true
        return true
    }

    // ---- incidents ----
    fun openInc(id: String) = incidents.firstOrNull { it.dev == id && it.status != "resolved" }
    private fun log(i: Inc, m: String) { i.log.add(LogE(System.currentTimeMillis(), m)) }

    private fun newInc(id: String, lvl: Int): Inc {
        val i = Inc("I" + java.lang.Long.toString(System.currentTimeMillis(), 36) + (Math.random() * 1000).toInt(), id, lvl, lvl, System.currentTimeMillis(), "open", "", ArrayList())
        log(i, "Detected: " + LVLN[lvl])
        incidents.add(0, i)
        while (incidents.size > 500) incidents.removeAt(incidents.size - 1)
        return i
    }

    /** Called for every reading of a drain. Returns true when something changed (so the caller saves). */
    fun track(st: DevState): Boolean {
        if (!st.online) return false
        val inc = openInc(st.id)
        if (st.lvl >= 2) {
            normalCount[st.id] = 0
            if (inc == null) { newInc(st.id, st.lvl); return true }
            if (st.lvl != inc.level) {
                inc.level = st.lvl
                if (st.lvl > inc.max) { inc.max = st.lvl; log(inc, "Escalated: " + LVLN[st.lvl]) }
                return true
            }
        } else if (st.lvl == 0 && inc != null) {
            val c = (normalCount[st.id] ?: 0) + 1
            normalCount[st.id] = c
            if (c >= 3) { inc.status = "resolved"; inc.end = System.currentTimeMillis(); inc.by = "Sensor (back to normal)"; log(inc, "Sensor reads normal: closed automatically"); return true }
        } else normalCount[st.id] = 0
        return false
    }

    private fun who() = officer.ifEmpty { "Official" }

    fun assign(id: String, team: String, lvl: Int): String {
        if (team.isEmpty()) return "Choose a maintenance team first."
        var inc = openInc(id)
        if (inc == null) { if (lvl < 1) return "Nothing to assign for this drain."; inc = newInc(id, lvl) }
        inc.team = team; inc.status = "assigned"; inc.assigned = System.currentTimeMillis()
        log(inc, "Assigned to $team by ${who()}")
        return ""
    }

    fun startWork(id: String) { openInc(id)?.let { it.status = "progress"; log(it, "Work started by " + it.team.ifEmpty { "team" }) } }
    fun resolve(id: String) { openInc(id)?.let { it.status = "resolved"; it.end = System.currentTimeMillis(); it.by = who(); log(it, "Marked resolved by ${who()}") } }
    fun addTeam(n: String): Boolean { val t = n.trim(); if (t.isNotEmpty() && t !in teams) { teams.add(t); return true }; return false }
    fun removeTeam(i: Int) { if (i in teams.indices) teams.removeAt(i) }

    // ---- officials PIN ----
    private fun sha(s: String) = MessageDigest.getInstance("SHA-256").digest(s.toByteArray()).joinToString("") { "%02x".format(it) }
    fun setPin(p: String): String {
        if (p.length < 4) return "PIN must be at least 4 characters."
        salt = java.lang.Long.toString((Math.random() * 1e14).toLong(), 16)
        pin = sha(salt + p); unlocked = true
        return "PIN set. It will be asked each time the app starts."
    }
    fun clearPin(): String { pin = null; return "PIN removed." }
    fun tryUnlock(p: String): Boolean { if (pin != null && sha(salt + p) == pin) unlocked = true; return unlocked }

    companion object {
        const val STALE_MS = 30000L
        const val CENTER_LAT = 13.0827
        const val CENTER_LNG = 80.2707
        val LVLN = listOf("Normal", "Possible blockage", "Blockage warning", "Overflow risk", "Overflow detected")
        val STAT = linkedMapOf("normal" to "Normal", "possible" to "Possible blockage", "blockage" to "Blockage detected", "overflow" to "Overflow warning", "offline" to "Offline")
        val STAT_COLOR = mapOf("normal" to 0xFF22B573, "possible" to 0xFFE6B800, "blockage" to 0xFFE8761F, "overflow" to 0xFFC0143C, "offline" to 0xFF8A8A8A)
        val INC_ST = mapOf("open" to "Open", "assigned" to "Assigned", "progress" to "In progress", "resolved" to "Resolved")
        val DEMO = mapOf(
            "demo-2" to Device("Anna Nagar 2nd Ave (demo)", "Ward 34", "Zone 5", 13.0850, 80.2101, true),
            "demo-3" to Device("T. Nagar Usman Rd (demo)", "Ward 57", "Zone 8", 13.0418, 80.2341, true)
        )
    }
}
