package com.techminds.flowbeacon

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin
import kotlin.random.Random

/** How Drip looks in each mood: eyes (o = open, c = closed), brows, mouth, arms, extras, motion. */
class DripLook(val eyes: Char, val brows: String?, val mouth: String, val left: String, val right: String, val extras: List<String>, val anim: String)

val DRIP_LOOKS = mapOf(
    "idle" to DripLook('o', null, "mouth_smile", "arm_left", "arm_right", emptyList(), "float"),
    "wave" to DripLook('o', "brows_up", "mouth_open", "arm_left", "arm_wave", emptyList(), "float"),
    "happy" to DripLook('c', null, "mouth_open", "arm_up2", "arm_up", emptyList(), "bounce"),
    "curious" to DripLook('o', "brows_up", "mouth_smile", "arm_left", "arm_right", emptyList(), "tilt"),
    "worried" to DripLook('o', "brows_worried", "mouth_worried", "arm_left", "arm_right", listOf("sweat_drop"), "shiver"),
    "alarmed" to DripLook('o', "brows_up", "mouth_open", "arm_up2", "arm_up", listOf("hardhat"), "hop"),
    "panic" to DripLook('o', "brows_worried", "mouth_scream", "arm_up2", "arm_up", listOf("hardhat", "sweat_drop"), "shake"),
    "think" to DripLook('o', null, "mouth_sleep", "arm_left", "arm_right", emptyList(), "float"),
    "sleep" to DripLook('c', null, "mouth_sleep", "arm_left", "arm_right", listOf("zzz"), "sleep"),
    "dizzy" to DripLook('o', "brows_worried", "mouth_worried", "arm_left", "arm_right", listOf("stars"), "tilt"),
    "cheer" to DripLook('c', "brows_up", "mouth_open", "arm_up2", "arm_up", listOf("tick"), "bounce"),
    // moods of its own, used when nothing is wrong (same as the web app)
    "yawn" to DripLook('c', null, "mouth_open", "arm_up2", "arm_up", emptyList(), "stretch"),
    "dance" to DripLook('c', null, "mouth_open", "arm_up2", "arm_up", emptyList(), "dance"),
    "sing" to DripLook('c', null, "mouth_open", "arm_left", "arm_right", emptyList(), "sway"),
    "giggle" to DripLook('c', null, "mouth_smile", "arm_left", "arm_right", emptyList(), "wiggle"),
    "gasp" to DripLook('o', "brows_up", "mouth_scream", "arm_up2", "arm_up", emptyList(), "hop"),
    "grumpy" to DripLook('o', "brows_angry", "mouth_worried", "arm_left", "arm_right", emptyList(), "shiver")
)

/** Drip, built from the original layered PNGs. [width] is the body width; the view is as tall as the body. */
@Composable
fun DripView(state: String, rain: Boolean, width: Dp, modifier: Modifier = Modifier, accent: String = "coral", calm: Boolean = false,
             squash: Float = 0f, spin: Float = 0f, lookX: Float = 0f) {
    val look = DRIP_LOOKS[state] ?: DRIP_LOOKS.getValue("idle")
    val tint = remember(accent) { tintFilter(accent) }
    val bodyH = width * (DripData.BODY_H / DripData.BODY_W)
    val tr = rememberInfiniteTransition(label = "drip")
    val t by tr.animateFloat(0f, 1f, infiniteRepeatable(tween(1600, easing = LinearEasing), RepeatMode.Restart), label = "t")
    var blink by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        while (true) { delay(3000L + Random.nextLong(2500)); blink = true; delay(140); blink = false }
    }
    val s = sin(t * 2 * PI).toFloat()
    val k = width.value / 150f
    var dx = 0f; var dy = 0f; var rot = 0f; var sx = 1f; var sy = 1f
    when (if (calm) "" else look.anim) {
        "float" -> dy = s * 3f
        "bounce" -> dy = -abs(s) * 12f
        "tilt" -> rot = s * 5f
        "shiver" -> dx = sin(t * 2 * PI * 25).toFloat() * 1.5f
        "hop" -> dy = -abs(sin(t * 2 * PI * 2)).toFloat() * 14f
        "shake" -> { val q = sin(t * 2 * PI * 22).toFloat(); dx = q * 3f; rot = q * 3f }
        "sleep" -> dy = s * 2f
        "stretch" -> { dy = -s * 4f; sy = 1f + 0.08f * s; sx = 1f - 0.04f * s }
        "dance" -> { val q = sin(t * 2 * PI * 4).toFloat(); dx = q * 8f; rot = q * 8f; dy = -abs(q) * 10f }
        "sway" -> { val q = sin(t * 2 * PI * 2).toFloat(); rot = q * 7f; dx = q * 5f }
        "wiggle" -> rot = sin(t * 2 * PI * 9).toFloat() * 5f
    }
    val closed = look.eyes == 'c' || blink
    val arms = listOf(look.left, look.right).toMutableList()
    val others = ArrayList<String>()
    others.add(if (closed) "eyes_closed" else "eyes_open")
    look.brows?.let { others.add(it) }
    others.add(look.mouth)
    others.addAll(look.extras)
    if (!closed) { others.add("pupil_l"); others.add("pupil_r") }
    if (rain) { others.add("umbrella"); arms[0] = "arm_up2" }

    @Composable
    fun Layer(name: String) {
        val p = DripData.POS[name] ?: return
        val src = if (name == "arm_up2") "arm_up" else name
        val sz = DripData.SIZE[src] ?: return
        val res = DripData.RES[src] ?: return
        val w = width * (p.third / 100f)
        val h = w * (sz.second.toFloat() / sz.first.toFloat())
        val x = width * (p.first / 100f) - w / 2
        val y = bodyH * (p.second / 100f) - h / 2
        val lk = if (name == "pupil_l" || name == "pupil_r") (lookX * 3f).dp else 0.dp
        var m: Modifier = Modifier.offset(x + lk, y).size(w, h)
        if (name == "arm_up2") m = m.graphicsLayer(scaleX = -1f)
        Image(painterResource(res), null, m, colorFilter = if (name in TINTED) tint else null)
    }

    Box(
        modifier.size(width, bodyH).offset((dx * k).dp, (dy * k).dp).graphicsLayer(
            scaleX = sx * (1f + 0.4f * squash), scaleY = sy * (1f - 0.4f * squash), rotationZ = rot + spin,
            transformOrigin = androidx.compose.ui.graphics.TransformOrigin(0.5f, 1f)
        )
    ) {
        arms.forEach { Layer(it) }
        Image(painterResource(DripData.RES.getValue("body")), null, Modifier.size(width, bodyH), colorFilter = tint)
        others.forEach { Layer(it) }
    }
}

private val TINTED = setOf("arm_left", "arm_right", "arm_up", "arm_up2", "arm_wave", "umbrella", "sweat_drop")

/** Recolours Drip's coral body for the other accents (the web app does this with a CSS hue-rotate filter). */
private fun tintFilter(accent: String): androidx.compose.ui.graphics.ColorFilter? {
    if (accent == "coral") return null
    if (accent == "black") {
        val g = floatArrayOf(0.15f, 0.295f, 0.055f, 0f, 0f, 0.15f, 0.295f, 0.055f, 0f, 0f, 0.15f, 0.295f, 0.055f, 0f, 0f, 0f, 0f, 0f, 1f, 0f)
        return androidx.compose.ui.graphics.ColorFilter.colorMatrix(androidx.compose.ui.graphics.ColorMatrix(g))
    }
    val deg = when (accent) { "blue" -> 205.0; "green" -> 125.0; "purple" -> 255.0; "red" -> -15.0; "yellow" -> 40.0; else -> 0.0 }
    val c = Math.cos(Math.toRadians(deg)).toFloat(); val s = Math.sin(Math.toRadians(deg)).toFloat()
    val m = floatArrayOf(
        0.213f + c * 0.787f - s * 0.213f, 0.715f - c * 0.715f - s * 0.715f, 0.072f - c * 0.072f + s * 0.928f, 0f, 0f,
        0.213f - c * 0.213f + s * 0.143f, 0.715f + c * 0.285f + s * 0.140f, 0.072f - c * 0.072f - s * 0.283f, 0f, 0f,
        0.213f - c * 0.213f - s * 0.787f, 0.715f - c * 0.715f + s * 0.715f, 0.072f + c * 0.928f + s * 0.072f, 0f, 0f,
        0f, 0f, 0f, 1f, 0f
    )
    return androidx.compose.ui.graphics.ColorFilter.colorMatrix(androidx.compose.ui.graphics.ColorMatrix(m))
}
