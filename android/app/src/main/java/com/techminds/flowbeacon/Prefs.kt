package com.techminds.flowbeacon

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest

data class Incident(
    val time: String, val cond: String, val cause: String, val ev: String,
    val sev: String, val conf: Int, val lvl: Int, val color: Long
)

/** Everything the app remembers, in plain SharedPreferences (no extra libraries). */
class Prefs(ctx: Context) {
    private val sp: SharedPreferences = ctx.getSharedPreferences("flowbeacon", Context.MODE_PRIVATE)

    var role: String
        get() = sp.getString("role", "") ?: ""
        set(v) = sp.edit().putString("role", v).apply()
    var mute: Boolean
        get() = sp.getBoolean("mute", false)
        set(v) = sp.edit().putBoolean("mute", v).apply()
    var vibrate: Boolean
        get() = sp.getBoolean("vibrate", true)
        set(v) = sp.edit().putBoolean("vibrate", v).apply()
    var vol: Float
        get() = sp.getFloat("vol", 0.6f)
        set(v) = sp.edit().putFloat("vol", v).apply()
    var drip: Boolean
        get() = sp.getBoolean("drip", true)
        set(v) = sp.edit().putBoolean("drip", v).apply()
    var ip: String
        get() = sp.getString("ip", "") ?: ""
        set(v) = sp.edit().putString("ip", v).apply()
    var accent: String
        get() = sp.getString("accent", "coral") ?: "coral"
        set(v) = sp.edit().putString("accent", v).apply()
    var mode: String
        get() = sp.getString("mode", "light") ?: "light"
        set(v) = sp.edit().putString("mode", v).apply()
    var calm: Boolean
        get() = sp.getBoolean("calm", false)
        set(v) = sp.edit().putBoolean("calm", v).apply()
    var node: String
        get() = sp.getString("node", "Drain 1") ?: "Drain 1"
        set(v) = sp.edit().putString("node", v).apply()
    fun sndOn(k: String): Boolean = sp.getBoolean("snd_$k", true)
    fun setSnd(k: String, v: Boolean) = sp.edit().putBoolean("snd_$k", v).apply()
    var devPw: String
        get() = sp.getString("devpw", "") ?: ""
        set(v) = sp.edit().putString("devpw", v).apply()

    var smsOn: Boolean
        get() = sp.getBoolean("sms_on", false)
        set(v) = sp.edit().putBoolean("sms_on", v).apply()
    var smsNums: String
        get() = sp.getString("sms_nums", "") ?: ""
        set(v) = sp.edit().putString("sms_nums", v).apply()
    var smsMin: Int
        get() = sp.getInt("sms_min", 3)
        set(v) = sp.edit().putInt("sms_min", v).apply()
    var smsCool: Int
        get() = sp.getInt("sms_cool", 5)
        set(v) = sp.edit().putInt("sms_cool", v).apply()

    var lang: String
        get() = sp.getString("lang", "en") ?: "en"
        set(v) = sp.edit().putString("lang", v).apply()
    var zoom: Float
        get() = sp.getFloat("zoom", 1f)
        set(v) = sp.edit().putFloat("zoom", v).apply()
    var notify: Boolean
        get() = sp.getBoolean("notify", true)
        set(v) = sp.edit().putBoolean("notify", v).apply()
    var bg: Boolean
        get() = sp.getBoolean("bg", true)
        set(v) = sp.edit().putBoolean("bg", v).apply()
    var upd: Boolean
        get() = sp.getBoolean("upd", true)
        set(v) = sp.edit().putBoolean("upd", v).apply()
    var quietOn: Boolean
        get() = sp.getBoolean("q_on", false)
        set(v) = sp.edit().putBoolean("q_on", v).apply()
    var quietFrom: String
        get() = sp.getString("q_from", "22:00") ?: "22:00"
        set(v) = sp.edit().putString("q_from", v).apply()
    var quietTo: String
        get() = sp.getString("q_to", "06:00") ?: "06:00"
        set(v) = sp.edit().putString("q_to", v).apply()
    var quietSms: Int
        get() = sp.getInt("q_sms", 3)
        set(v) = sp.edit().putInt("q_sms", v).apply()
    var useModel: Boolean
        get() = sp.getBoolean("use_model", false)
        set(v) = sp.edit().putBoolean("use_model", v).apply()
    var modelJson: String
        get() = sp.getString("model", "") ?: ""
        set(v) = sp.edit().putString("model", v).apply()
    var profilesJson: String
        get() = sp.getString("profiles", "[]") ?: "[]"
        set(v) = sp.edit().putString("profiles", v).apply()
    var mapJson: String
        get() = sp.getString("map", "") ?: ""
        set(v) = sp.edit().putString("map", v).apply()
    var nodesJson: String
        get() = sp.getString("nodes", "{}") ?: "{}"
        set(v) = sp.edit().putString("nodes", v).apply()

    var cfg: Cfg
        get() {
            val d = Cfg()
            return Cfg(
                sp.getFloat("c_dropWarn", d.dropWarn.toFloat()).toDouble(), sp.getFloat("c_dropBlock", d.dropBlock.toFloat()).toDouble(),
                sp.getFloat("c_rise", d.rise.toFloat()).toDouble(), sp.getFloat("c_risk", d.risk.toFloat()).toDouble(),
                sp.getFloat("c_over", d.over.toFloat()).toDouble(), sp.getFloat("c_turb", d.turb.toFloat()).toDouble()
            )
        }
        set(c) = sp.edit().putFloat("c_dropWarn", c.dropWarn.toFloat()).putFloat("c_dropBlock", c.dropBlock.toFloat())
            .putFloat("c_rise", c.rise.toFloat()).putFloat("c_risk", c.risk.toFloat())
            .putFloat("c_over", c.over.toFloat()).putFloat("c_turb", c.turb.toFloat()).apply()

    var base: Base?
        get() {
            val s = sp.getString("base", null) ?: return null
            return try {
                val o = JSONObject(s)
                Base(o.getDouble("flow"), o.getDouble("dist"), o.getDouble("turb"), o.getDouble("sf"), o.getDouble("sd"), o.getDouble("st"))
            } catch (e: Exception) { null }
        }
        set(b) {
            if (b == null) sp.edit().remove("base").apply()
            else sp.edit().putString("base", JSONObject().put("flow", b.flow).put("dist", b.dist).put("turb", b.turb)
                .put("sf", b.sf).put("sd", b.sd).put("st", b.st).toString()).apply()
        }

    fun loadIncidents(): List<Incident> = try {
        val a = JSONArray(sp.getString("inc", "[]"))
        (0 until a.length()).map {
            val o = a.getJSONObject(it)
            Incident(o.getString("time"), o.getString("cond"), o.getString("cause"), o.getString("ev"),
                o.getString("sev"), o.getInt("conf"), o.getInt("lvl"), o.getLong("c"))
        }
    } catch (e: Exception) { emptyList() }

    fun saveIncidents(list: List<Incident>) {
        val a = JSONArray()
        list.take(200).forEach {
            a.put(JSONObject().put("time", it.time).put("cond", it.cond).put("cause", it.cause).put("ev", it.ev)
                .put("sev", it.sev).put("conf", it.conf).put("lvl", it.lvl).put("c", it.color))
        }
        sp.edit().putString("inc", a.toString()).apply()
    }

    companion object {
        private const val SALT = "fb-dev:"
        fun hash(p: String): String =
            MessageDigest.getInstance("SHA-256").digest((SALT + p).toByteArray()).joinToString("") { "%02x".format(it) }
        val DEFAULT_HASH: String by lazy { hash("1234") }
    }
}
