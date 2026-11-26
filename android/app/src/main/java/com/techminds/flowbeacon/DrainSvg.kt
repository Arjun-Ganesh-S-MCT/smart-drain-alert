package com.techminds.flowbeacon

import android.content.Context
import android.graphics.Canvas
import android.os.SystemClock
import android.view.View
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.caverock.androidsvg.SVG
import java.util.Locale
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

/** Animated values behind the drain cross-section (water height, wave, pipe flow, blockage). Port of drain.py. */
class DrainState {
    var y = 167 - 0.5 * 134
    var p = 0.5
    var amp = 1.2
    var phase = 0.0
    var t = 0.0
    var flowSpeed = 0.0
    var debris = 0.0
    var debrisTarget = 0.0
    var turb = 0.0
    var rain = false
    var calm = false
    var pipePhase = 0.0
    private val drops = Array(9) { doubleArrayOf(28.0 + (it * 37 % 104), (it * 11 % 30).toDouble(), 40.0 + (it * 13 % 60)) }

    fun setValues(p: Double, flowRatio: Double, blocked: Boolean, turbidity: Double, raining: Boolean, calmMode: Boolean) {
        val ny = 167 - p.coerceIn(0.0, 1.0) * 134
        this.p = p
        if (!calmMode && abs(ny - y) > 0.4) amp = min(7.0, amp + abs(ny - y) * 1.2)
        y = ny; debrisTarget = if (blocked) 1.0 else 0.0
        turb = turbidity.coerceIn(0.0, 1.0); rain = raining; calm = calmMode
        flowSpeed = if (flowRatio <= 0) 0.0 else max(0.4, min(6.0, 1.2 / max(flowRatio, 0.1)))
    }

    fun step(dt: Double) {
        t += dt; phase += dt * 3.2
        amp = max(if (flowSpeed > 0) 1.2 else 0.7, amp - dt * 2.2)
        debris += (debrisTarget - debris) * min(1.0, dt * 6)
        if (flowSpeed > 0 && !calm) pipePhase = (pipePhase + dt / flowSpeed) % 1.0
        if (rain && !calm) for (d in drops) { d[1] += d[2] * dt; if (d[1] > 30) d[1] = 0.0 }
    }

    private fun f(x: Double, n: Int = 1) = String.format(Locale.US, "%.${n}f", x)
    private fun mix(a: IntArray, b: IntArray, k: Double) = "rgb(" + (0..2).joinToString(",") { (a[it] + (b[it] - a[it]) * k).roundToInt().toString() } + ")"

    fun svg(tpl: String): String {
        val pts = (0..12).map { Pair(23 + it * 114.0 / 12, y + amp * sin(phase + it * 0.9)) }
        val surf = "M" + pts.joinToString(" L") { f(it.first) + " " + f(it.second, 2) }
        val water = "M23 168 L23 " + f(y) + pts.joinToString("") { " L" + f(it.first) + " " + f(it.second, 2) } + " L137 168 Z"
        val sp = 6 + max(0.0, y - 48) * 0.16
        val rep = HashMap<String, String>()
        rep["WATER"] = water; rep["SURF"] = surf
        for (i in 0..2) rep["P${i + 1}"] = if (p > Core.PROBE_P[i]) "1.0" else "0.22"      // a probe lights up when the water is above it
        rep["BEAM"] = "70,48 90,48 ${f(90 + sp)},${f(y)} ${f(70 - sp)},${f(y)}"
        rep["WG1"] = mix(intArrayOf(86, 170, 220), intArrayOf(168, 128, 74), turb)
        rep["WG2"] = mix(intArrayOf(40, 110, 170), intArrayOf(104, 74, 40), turb)
        rep["DEBRIS"] = f(debris, 2)
        val tt = if (calm) 0.0 else t
        rep["LED"] = f(1.0 - 0.75 * (0.5 - 0.5 * cos(tt * 2 * PI / 1.6)), 2)
        rep["PIPE"] = f(-36 * pipePhase); rep["PIPE2"] = f(-36 * ((pipePhase + 0.1) % 1.0))
        rep["WET"] = if (rain) f(1.0 - 0.75 * (0.5 - 0.5 * cos(tt * 2 * PI)), 2) else "0"
        val base = intArrayOf(56, 63, 70); val q = intArrayOf(62, 72, 82)
        for (i in 0..2) {
            val k = (tt / 1.8 - i * 0.14).let { ((it % 1.0) + 1.0) % 1.0 }
            val o = if (calm) 0.0 else if (k < 0.3) k / 0.3 * 0.9 else 0.9 * (1 - (k - 0.3) / 0.7)
            val dy = -4 + 12 * k
            rep["S${i + 1}O"] = f(max(0.0, o), 2); rep["S${i + 1}Y"] = f(base[i] + dy); rep["S${i + 1}Q"] = f(q[i] + dy)
        }
        val by = intArrayOf(160, 164, 158)
        for (i in 0..2) {
            val k = ((tt / 4.0) + i * 0.33) % 1.0
            rep["B${i + 1}Y"] = f(by[i] - 70 * k)
            rep["B${i + 1}O"] = if (calm) "0" else f(if (k > 0.15) 0.5 * (1 - k) / 0.85 else 0.5 * k / 0.15, 2)
        }
        rep["DROPS"] = if (rain) drops.joinToString("") { "<circle cx=\"${it[0].roundToInt()}\" cy=\"${f(it[1] + 2)}\" r=\"3.2\"/>" } else ""
        var out = tpl
        for ((k, v) in rep) out = out.replace("{{$k}}", v)
        return out
    }
}

private class DrainViewN(ctx: Context, private val tpl: String, private val st: DrainState) : View(ctx) {
    private var last = 0L
    override fun onDraw(canvas: Canvas) {
        val now = SystemClock.uptimeMillis()
        if (last != 0L) st.step(min(0.1, (now - last) / 1000.0))
        last = now
        try {
            val svg = SVG.getFromString(st.svg(tpl))
            svg.setDocumentWidth(width.toFloat()); svg.setDocumentHeight(height.toFloat())
            svg.renderToCanvas(canvas)
        } catch (e: Exception) {
            // keep the last frame
        }
        postInvalidateDelayed(60)
    }
}

/** The drain cross-section: the web app's artwork, animated with the live readings. */
@Composable
fun DrainPicture(vm: AppVm, modifier: Modifier = Modifier) {
    val ctx = LocalContext.current
    val tpl = remember { ctx.assets.open("drain.svg.tpl").bufferedReader().use { it.readText() } }
    val st = remember { DrainState() }
    val s = vm.snap; val b = vm.base; val c = vm.cfg; val calm = vm.calm
    SideEffect {
        if (s != null) {
            val p = Core.levelP(s.d.dist)          // the 3-probe sensor: the water is drawn at the step it reads
            val fl = if (b != null && b.flow > 0) s.d.flow / b.flow else if (s.d.flow > 0) 1.0 else 0.0
            val tb = if (b != null && b.turb > 0) (s.d.turb / b.turb - 1) / 1.2 else (s.d.turb - 800) / 800
            st.setValues(p, if (s.d.flow > 0.05) fl else 0.0, s.e.fd >= c.dropWarn / 100, tb, s.d.rain, calm)
        }
    }
    AndroidView(factory = { DrainViewN(it, tpl, st) }, modifier = modifier.fillMaxWidth().aspectRatio(560f / 220f).clip(RoundedCornerShape(14.dp)))
}
