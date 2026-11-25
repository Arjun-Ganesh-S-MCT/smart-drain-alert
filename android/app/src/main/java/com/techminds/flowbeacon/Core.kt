package com.techminds.flowbeacon

import java.util.Locale
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sqrt

/** Analysis core: a port of src/core.js (blockage and overflow evaluation). Pure Kotlin, no Android classes. */

data class Cfg(
    val dropWarn: Double = 25.0, val dropBlock: Double = 50.0, val rise: Double = 1.0,
    val risk: Double = 4.0, val over: Double = 2.0, val turb: Double = 30.0
)

data class Base(val flow: Double, val dist: Double, val turb: Double, val sf: Double, val sd: Double, val st: Double)
data class Reading(val flow: Double, val dist: Double, val turb: Double, val rain: Boolean)
data class Sample(val t: Long, val f: Double, val l: Double)
data class Health(val issues: List<String>, val bad: Boolean)
data class Eval(val lvl: Int, val ev: List<String>, val cause: String, val conf: Int, val fd: Double, val rise: Double)
data class Level(val name: String, val color: Long, val sev: String, val icon: String)

object Core {
    val LEVELS = listOf(
        Level("Normal", 0xFF22B573, "None", "✓"),
        Level("Possible blockage", 0xFFE6B800, "Low", "?"),
        Level("Blockage warning", 0xFFE8761F, "Medium", "▲"),
        Level("Overflow risk", 0xFFEF4444, "High", "■"),
        Level("Overflow detected", 0xFFC0143C, "Critical", "✖")
    )

    private fun f(fmt: String, vararg a: Any) = String.format(Locale.US, fmt, *a)

    // The water level comes from a 5-step sensor (five probes, each with a transistor). The Arduino reports how many are wet
    // ("lv", 0 to 5); the app turns that into a distance from the sensor top so the rest of the logic is unchanged.
    const val EMPTY_CM = 18.0       // distance when no probe is wet (keep the same as EMPTY_CM in the firmware)
    const val STEP_CM = 3.0         // height between two probes
    fun level5(dist: Double): Int = Math.round((EMPTY_CM - dist) / STEP_CM).toInt().coerceIn(0, 5)
    fun distFromLv(lv: Int): Double = EMPTY_CM - lv.coerceIn(0, 5) * STEP_CM
    fun q5(dist: Double): Double = distFromLv(level5(dist))

    fun health(d: Reading, hist: List<Sample>, base: Base?): Health {
        val r = hist.takeLast(20)
        val issues = ArrayList<String>()
        val bad = d.dist <= 0 || d.dist > 600
        if (bad) issues.add("Water level sensor reading out of range, check wiring")
        if (d.turb <= 0 || d.turb >= 4095) issues.add("Turbidity reading at its limit")
        if (r.size >= 20) {
            if (r.all { it.l == d.dist }) issues.add("Water level has not changed for a long time")
            if (d.flow > 0 && r.all { it.f == d.flow }) issues.add("Flow value is frozen")
        }
        if (base != null && d.flow == 0.0) issues.add("Flow is 0: blockage or sensor fault")
        return Health(issues, bad)
    }

    /** Seconds until the water reaches the overflow distance at the current rate, or null. */
    fun predictEta(hist: List<Sample>, over: Double): Double? {
        val p = hist.takeLast(20)
        if (p.size < 10) return null
        val n = p.size
        val t0 = p[0].t
        var sx = 0.0; var sy = 0.0; var sxy = 0.0; var sxx = 0.0
        for (q in p) {
            val x = (q.t - t0) / 1000.0
            sx += x; sy += q.l; sxy += x * q.l; sxx += x * x
        }
        val den = n * sxx - sx * sx
        if (den == 0.0) return null
        val m = (n * sxy - sx * sy) / den
        val cur = p[n - 1].l
        if (m > -0.005 || cur <= over) return null
        return (cur - over) / -m
    }

    fun evaluate(d: Reading, bad: Boolean, b: Base?, cfg: Cfg): Eval {
        val dw = cfg.dropWarn / 100; val db = cfg.dropBlock / 100; val tb = cfg.turb / 100
        var lvl = 0
        val ev = ArrayList<String>()
        var pts = 0
        var fd = 0.0; var rise = 0.0; var td = 0.0; var z = 0.0
        var cause = "No fault indicated"
        if (b != null) {
            fd = if (b.flow > 0) 1 - d.flow / b.flow else 0.0
            rise = if (bad) 0.0 else b.dist - d.dist
            td = if (b.turb > 0) (d.turb - b.turb) / b.turb else 0.0
            z = max(abs(d.flow - b.flow) / b.sf, if (bad) 0.0 else abs(d.dist - b.dist) / b.sd)
            if (fd > 0.05) ev.add("Flow " + (-fd * 100).roundToInt() + "% vs baseline")
            if (rise > 0.2) ev.add(f("Level +%.1f cm", rise))
            if (abs(td) > 0.1) ev.add("Turbidity " + (if (td > 0) "+" else "") + (td * 100).roundToInt() + "%")
            if (z > 3) ev.add(f("Anomaly %.1f σ", z))
        }
        if (d.rain) ev.add("Rain plate wet")
        val blk = fd >= dw; val rising = rise >= cfg.rise; val dirty = td >= tb
        if (b != null) {
            if (blk && (rising || dirty)) lvl = 1
            if (fd >= db && rising) lvl = 2
            if (z > 4 && fd > 0.1 && lvl == 0) lvl = 1
        }
        if (!bad) {
            if (d.dist <= cfg.risk) lvl = max(lvl, 3)
            if (d.dist <= cfg.over) lvl = 4
        }
        cause = when {
            blk && d.rain -> "Blockage and rainfall likely both contributing"
            blk -> "Likely blockage: flow falling" + (if (rising) " while level rises" else "")
            d.rain && rising -> "Rainfall likely contributing to rising level"
            lvl >= 3 -> "Water level high; cause unclear"
            lvl > 0 -> "Unusual pattern against baseline"
            else -> cause
        }
        if (blk) pts += if (fd >= db) 40 else 25
        if (rising) pts += 25
        if (dirty) pts += 15
        if (d.rain && rising) pts += 10
        if (lvl >= 3) pts += 15
        if (z > 3) pts += 10
        return Eval(lvl, ev, cause, if (lvl > 0) min(95, pts) else 0, fd, rise)
    }

    fun baseFrom(rows: List<Reading>): Base {
        val n = rows.size
        fun mean(sel: (Reading) -> Double) = rows.sumOf(sel) / n
        fun sd(sel: (Reading) -> Double, floor: Double): Double {
            val mu = mean(sel)
            return max(sqrt(rows.sumOf { (sel(it) - mu).pow(2) } / n), floor)
        }
        val mf = mean { it.flow }
        return Base(mf, mean { it.dist }, mean { it.turb },
            sd({ it.flow }, max(0.05, 0.05 * mf)), sd({ it.dist }, 0.2), sd({ it.turb }, 10.0))
    }

    fun normNum(v: String): String? {
        var d = v.replace(Regex("[\\s\\-()]"), "")
        d = when {
            Regex("^\\d{10}$").matches(d) -> "+91$d"
            Regex("^0\\d{10}$").matches(d) -> "+91" + d.substring(1)
            Regex("^91\\d{10}$").matches(d) -> "+$d"
            else -> d
        }
        return if (Regex("^\\+\\d{10,15}$").matches(d)) d else null
    }
}

/** Drip's offline assistant (port of src/drip-core.js, English). */
object DripChat {
    private val lines = mapOf(
        "curious" to "Flow is lower than normal at {d}. Keep watching.",
        "worried" to "Blockage warning at {d}: flow is falling while the level rises. Inspect the drain.",
        "alarmed" to "Overflow risk at {d}. Check the drain now.",
        "panic" to "Overflow detected at {d}. Act now.",
        "sleep" to "No data. Waiting for the board.",
        "think" to "Calibrating. Keep the flow steady.",
        "dizzy" to "A sensor reading looks wrong. Check the wiring."
    )
    val tips = listOf(
        "Plastic and silt are the top causes of clogged drains.",
        "A drain can lose half its flow before anyone notices.",
        "Flow falling while the level rises is the classic blockage sign.",
        "The rain plate only knows wet or dry. It cannot measure how hard it rains.",
        "Turbidity is cloudiness. More particles in the water means a higher reading.",
        "Clearing drains before the monsoon prevents most street flooding."
    )
    const val HELP = "Ask me: status, why, when will it overflow, or what turbidity, flow, the water level, calibration or SMS mean. " +
        "I can also set the baseline, start the demo, mute or acknowledge an alarm."

    fun line(state: String): String? = lines[state]?.replace("{d}", "the drain")

    class Ctx(val worst: Int, val live: Boolean, val statusText: String, val cause: String, val evid: String, val pred: String)
    class Reply(val text: String, val action: String? = null)

    fun reply(text: String, c: Ctx): Reply {
        val t = text.lowercase().trim()
        fun has(p: String) = Regex(p).containsMatchIn(t)
        if (t.isEmpty()) return Reply("Ask me something. Try: help")
        if (has("\\bbaseline\\b")) return Reply("Setting the baseline. Keep the flow normal for a few seconds.", "baseline")
        if (has("\\bdemo\\b")) return Reply("Starting or stopping the demo.", "demo")
        if (has("\\b(unmute|sound on)\\b")) return Reply("Sound is on.", "unmute")
        if (has("\\b(mute|silence)\\b") && !has("alarm")) return Reply("Sound is off.", "mute")
        if (has("\\b(acknowledge|ack|silence alarm|stop (the )?alarm)\\b")) return Reply("Alarm acknowledged.", "ack")
        if (has("how are you|are you ok|systems"))
            return Reply(if (c.worst >= 2) "Something needs attention. Ask me for the status." else "All systems are running. Nothing needs attention.")
        if (has("\\b(status|drains?|how is|how are the|condition)\\b") && !has("what is|what are"))
            return Reply(if (!c.live) "No readings yet. Connect the board or try the demo." else c.statusText + ".")
        if (has("\\b(why|cause|reason)\\b")) {
            if (c.cause.isNotEmpty() && c.cause != "No fault indicated")
                return Reply(c.cause + (if (c.evid.isNotEmpty()) ". Evidence: " + c.evid else "") + ".")
            return Reply("Nothing is wrong right now.")
        }
        if (has("(when|will).*(overflow|flood|full)|predict|\\beta\\b"))
            return Reply(if (c.pred.isNotEmpty()) c.pred else "No overflow is predicted right now.")
        if (has("turbidity|cloudy")) return Reply("Turbidity is how cloudy the water is. More silt or mud gives a higher reading, which can support a blockage estimate.")
        if (has("ultrasonic|distance|level|probe|sensor")) return Reply("The water level sensor has five probes at different heights, each with a transistor. The level is how many probes are wet, from 0 to 5. More wet probes means higher water.", null)
        if (has("\\bflow\\b")) return Reply("The flow sensor counts pulses. Flow falling while the water level rises is the classic blockage sign.")
        if (has("calibrat")) return Reply("Calibration teaches the app what normal looks like. Use the wizard under Calibration, then tune the sliders.")
        if (has("\\b(sms|text message)\\b")) return Reply("SMS needs a GSM module on the board. Add your number under Connection and press Send test SMS.")
        if (has("wi-?fi|usb|cable|connect")) return Reply("The Arduino Nano connects with a USB cable. Plug it into the phone with an OTG cable, tap Find board and then Connect.", null)
        if (has("\\brain\\b")) return Reply("The rain plate only knows wet or dry. It cannot measure how hard it rains.")
        if (has("\\btip\\b|\\bfact\\b|did you know")) return Reply(tips.random())
        if (has("who are you|your name|about you|what are you")) return Reply("I am Drip, the FlowBeacon assistant. I watch your drains and tell you what changes.")
        if (has("thank|thanks|nandri")) return Reply("You are welcome.")
        if (has("(^|\\b)(hi|hello|hey|vanakkam)\\b")) return Reply("Hello. Ask me for the status any time.")
        if (has("help|what can you do|commands")) return Reply(HELP)
        return Reply("I did not understand that. Try: status, why, tip or help.")
    }
}
