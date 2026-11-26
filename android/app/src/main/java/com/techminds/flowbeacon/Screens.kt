package com.techminds.flowbeacon

import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.runtime.LaunchedEffect
import android.content.Intent
import androidx.compose.animation.animateColor
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import java.util.Locale
import kotlin.math.roundToInt

// ------------------------------------------------------------------ root
@Composable
fun AppRoot(vm: AppVm) {
    FlowTheme(vm.accent, vm.mode) {
      val dens = androidx.compose.ui.platform.LocalDensity.current
      androidx.compose.runtime.CompositionLocalProvider(
          LocalSound provides vm.sound, LocalLang provides vm.lang,
          androidx.compose.ui.platform.LocalDensity provides androidx.compose.ui.unit.Density(dens.density, dens.fontScale * vm.zoom)
      ) {
        Box(Modifier.fillMaxSize().background(FB.BG)) {
            var introDone by rememberSaveable { mutableStateOf(false) }
            when {
                !introDone -> IntroScreen { introDone = true }
                !vm.roleChosen -> RoleScreen(vm)
                else -> MainScreen(vm)
            }
        }
      }
    }
}

private val TABS = listOf(
    Triple("overview", "Overview", "devices"), Triple("model", "Drain model", "zone"), Triple("incidents", "Incidents", "blockage"),
    Triple("connect", "Connection", "connect"), Triple("history", "History", "resolved"), Triple("calib", "Calibration", "calibration"),
    Triple("drip", "Ask Drip", "team"), Triple("settings", "Settings", "status"), Triple("console", "Console", "update"), Triple("map", "City map", "map")
)

@Composable
fun MainScreen(vm: AppVm) {
    var tab by rememberSaveable { mutableStateOf("overview") }
    val tabs = Roles.tabs(vm.role)
    val cur = if (tab in tabs) tab else "overview"
    Column(Modifier.fillMaxSize()) {
        Header(vm)
        Toolbar(vm) { tab = it }
        if (vm.banner.isNotEmpty()) AlarmBanner(vm)
        UpdateBar(vm)
        Box(Modifier.weight(1f).fillMaxWidth()) {
            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(start = 22.dp, end = 22.dp, top = 14.dp, bottom = 130.dp),
                verticalArrangement = Arrangement.spacedBy(22.dp)
            ) {
                when (cur) {
                    "overview" -> OverviewPage(vm)
                    "model" -> ModelPage(vm)
                    "incidents" -> IncidentsPage(vm)
                    "connect" -> ConnectPage(vm)
                    "calib" -> CalibPage(vm)
                    "drip" -> DripPage(vm)
                    "settings" -> SettingsPage(vm)
                    "console" -> ConsolePage(vm)
                    "history" -> HistoryPage(vm)
                    "map" -> CityMapPage(vm)
                }
            }
            // Drip stands on the top edge of the menu bar: it lives inside the content area, so it can never fall behind the bar
            if (vm.dripOn) DripOverlay(vm, Modifier.align(Alignment.BottomEnd))
        }
        BottomBar(tabs, cur) { tab = it }
    }
}

@Composable
fun Header(vm: AppVm) {
    Column(Modifier.fillMaxWidth().padding(start = 18.dp, end = 18.dp, top = 8.dp, bottom = 6.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Image(painterResource(R.drawable.img_techminds), "TechMinds", Modifier.height(42.dp))
            T("FlowBeacon", Modifier.padding(start = 12.dp).weight(1f), 18, true, maxLines = 1)
            NeuButton((Roles.NAME[vm.role] ?: "") + " ▾", { vm.openChooser() })
        }
        ConnChip(vm.connLabel, if (vm.connected) Color(0xFF22B573) else if (vm.demo) Color(0xFFE8B422) else FB.MU)
    }
}

@Composable
fun Toolbar(vm: AppVm, go: (String) -> Unit) {
    NeuCard(Modifier.padding(horizontal = 18.dp), pad = PaddingValues(horizontal = 14.dp, vertical = 12.dp)) {
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            if (vm.role != "consumer") {                       // removed in Consumer mode, never greyed out
                NeuButton("Connect Arduino Nano", { go("connect") }, icon = "connect", main = true, tall = true)
                NeuButton("Demo mode", { vm.toggleDemo() }, icon = "demo", on = vm.demo, tall = true)
                NeuButton("Set baseline", { vm.startBaseline() }, icon = "baseline", tall = true)
                NeuButton("Calibration", { go("incidents"); vm.wizardStart() }, icon = "calibration", tall = true)
                Sep()
            }
            Sub("Sound")
            NeuSwitch(!vm.mute, { vm.setMuted(!it) })
            NeuSlider(vm.vol, { vm.setVolume(it) }, Modifier.width(110.dp))
            Sep()
            Sub("Drip")
            NeuSwitch(vm.dripOn, { vm.updateDripOn(it) })
        }
    }
}

@Composable
fun AlarmBanner(vm: AppVm) {
    val tr = rememberInfiniteTransition(label = "ban")
    val c by tr.animateColor(Color(0xFFA8212E), Color(0xFFD6483F), infiniteRepeatable(tween(1000), RepeatMode.Reverse), label = "c")
    Row(Modifier.padding(horizontal = 18.dp, vertical = 8.dp).fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(c).padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
        T(vm.banner, Modifier.weight(1f), 13, true, Color.White)
        Box(Modifier.clip(RoundedCornerShape(50)).background(Color.White).clickable { vm.acknowledge() }.padding(horizontal = 14.dp, vertical = 9.dp)) {
            T("Acknowledge", size = 12, bold = true, color = Color(0xFFA8212E))
        }
    }
}

@Composable
fun BottomBar(tabs: List<String>, cur: String, pick: (String) -> Unit) {
    val sd = FB.SD; val sl = FB.SL
    val snd = LocalSound.current
    Row(
        Modifier.fillMaxWidth().background(FB.BG).drawBehind {
            drawRect(sd, Offset.Zero, androidx.compose.ui.geometry.Size(size.width, 1.dp.toPx()))
            drawRect(sl, Offset(0f, 1.dp.toPx()), androidx.compose.ui.geometry.Size(size.width, 1.dp.toPx()))
        }.horizontalScroll(rememberScrollState()).padding(horizontal = 10.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        TABS.filter { it.first in tabs }.forEach { (k, name, ic) ->
            val sel = k == cur
            Column(
                Modifier.widthIn(min = 70.dp).let { if (sel) it.neu("inset") else it }.clip(RoundedCornerShape(14.dp)).clickable { snd?.play("click"); pick(k) }.padding(horizontal = 10.dp, vertical = 7.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Ico(ic, 22.dp)
                T(name, size = 10, bold = true, color = if (sel) FB.AC else FB.TX, maxLines = 1)
            }
        }
    }
}


// ------------------------------------------------------------------ Drip overlay
class DripPart(var x: Float, var y: Float, var vx: Float, var vy: Float, var life: Float, val color: Color, val size: Float)

/** Drip on screen: drag it, throw it (it falls with gravity, bounces and squashes), tap it (3 taps giggle, 5 taps make it dizzy). */
@Composable
fun DripOverlay(vm: AppVm, modifier: Modifier) {
    val density = androidx.compose.ui.platform.LocalDensity.current
    val cfg = androidx.compose.ui.platform.LocalConfiguration.current
    val d = density.density
    val maxLeft = with(density) { (cfg.screenWidthDp.dp - 78.dp - 16.dp).toPx() }
    val maxUp = with(density) { (cfg.screenHeightDp.dp - 220.dp).toPx() }
    var ox by remember { mutableStateOf(0f) }
    var oy by remember { mutableStateOf(0f) }
    var squash by remember { mutableStateOf(0f) }
    var tick by remember { mutableStateOf(0) }
    val parts = remember { ArrayList<DripPart>() }
    val spin = remember { Animatable(0f) }
    val scope = rememberCoroutineScope()
    var fall by remember { mutableStateOf<kotlinx.coroutines.Job?>(null) }
    var vx by remember { mutableStateOf(0f) }
    var vy by remember { mutableStateOf(0f) }
    var taps by remember { mutableStateOf(listOf<Long>()) }
    var throws by remember { mutableStateOf(listOf<Long>()) }

    fun burst(n: Int, confetti: Boolean) {
        val cols = if (confetti) listOf(Color(0xFFFC8068), Color(0xFFE6B800), Color(0xFF22B573), Color(0xFF4F86C6), Color(0xFF8A6BC9)) else listOf(Color(0xFF4FA8E0), Color(0xFF7CC4F0), Color(0xFFA8DCF8))
        for (i in 0 until n) {
            val a = i.toFloat() / n * 6.2832f + (Math.random().toFloat() - 0.5f) * 0.4f
            val v = (120f + Math.random().toFloat() * 180f) * d
            parts.add(DripPart(39f * d, 50f * d, kotlin.math.cos(a) * v, kotlin.math.sin(a) * v - 120f * d, 1f, cols[i % cols.size], (4f + Math.random().toFloat() * 4f) * d))
        }
    }

    // one loop for the particles and the squash
    LaunchedEffect(Unit) {
        var last = withFrameNanos { it }
        while (true) {
            val now = withFrameNanos { it }
            val dt = ((now - last) / 1e9f).coerceAtMost(0.05f); last = now
            if (squash > 0.001f) squash *= 0.82f
            if (parts.isNotEmpty()) {
                parts.forEach { it.vy += 900f * d * dt; it.x += it.vx * dt; it.y += it.vy * dt; it.life -= dt * 1.2f }
                parts.removeAll { it.life <= 0f }
                tick++
            }
        }
    }
    LaunchedEffect(vm.dripSpin) { if (vm.dripSpin > 0) { spin.snapTo(0f); spin.animateTo(360f, androidx.compose.animation.core.tween(900)); spin.snapTo(0f) } }

    fun startFall() {
        fall?.cancel()
        fall = scope.launch {
            var last = withFrameNanos { it }
            while (true) {
                val now = withFrameNanos { it }
                val dt = ((now - last) / 1e9f).coerceAtMost(0.05f); last = now
                vy += 1900f * d * dt
                ox += vx * dt; oy += vy * dt
                if (oy >= 0f) {
                    oy = 0f
                    if (vy > 140f * d) { if (vy > 260f * d) { squash = minOf(0.5f, vy / (1600f * d)); burst(6, false) }; vy = -vy * 0.52f; vx *= 0.88f } else vy = 0f
                    vx *= 0.6f
                }
                if (oy < -maxUp) { oy = -maxUp; vy = -vy * 0.5f }
                if (ox < -maxLeft) { ox = -maxLeft; vx = -vx * 0.6f }
                if (ox > 0f) { ox = 0f; vx = -vx * 0.6f }
                if (kotlin.math.abs(vx) < 6f * d && kotlin.math.abs(vy) < 6f * d && oy >= -1f) { vx = 0f; vy = 0f; break }
            }
        }
    }

    Column(modifier.padding(end = 8.dp), horizontalAlignment = Alignment.End) {
        if (vm.dripSayText.isNotEmpty()) {
            Box(Modifier.widthIn(max = 240.dp).padding(bottom = 10.dp, start = 12.dp).neu("card").padding(horizontal = 14.dp, vertical = 10.dp)) {
                T(vm.dripSayText, size = 12, bold = true)
            }
        }
        Box(
            Modifier.offset { IntOffset(ox.roundToInt(), oy.roundToInt()) }
                .drawWithContent {
                    drawContent()
                    if (tick >= 0) parts.forEach { drawCircle(it.color.copy(alpha = it.life.coerceIn(0f, 1f)), it.size / 2f, Offset(it.x, it.y)) }
                }
                .pointerInput(Unit) {
                    detectTapGestures {
                        val now = System.currentTimeMillis()
                        taps = taps.filter { t -> now - t < 1400 } + now
                        when {
                            taps.size >= 5 -> { taps = emptyList(); vm.dripFlash("dizzy", 2500, "Whoa, too many taps!"); burst(8, false) }
                            taps.size >= 3 -> { vm.dripFlash("giggle", 1600, "Hehe, that tickles!"); burst(10, true) }
                            else -> { burst(6, false); vm.dripTap() }
                        }
                    }
                }
                .pointerInput(Unit) {
                    var lastT = 0L
                    detectDragGestures(
                        onDragStart = { fall?.cancel(); vx = 0f; vy = 0f; lastT = System.currentTimeMillis() },
                        onDragEnd = {
                            val now = System.currentTimeMillis()
                            if (now - lastT > 100) { vx = 0f; vy = 0f }
                            throws = throws.filter { t -> now - t < 6000 } + now
                            if (throws.size >= 3) { throws = emptyList(); vm.dripFlash("dizzy", 2600, "I am dizzy… stop throwing me!") }
                            startFall()
                        },
                        onDragCancel = { startFall() }
                    ) { change, drag ->
                        change.consume()
                        val now = System.currentTimeMillis()
                        val dt = maxOf(0.016f, (now - lastT) / 1000f); lastT = now
                        ox = (ox + drag.x).coerceIn(-maxLeft, 0f); oy = (oy + drag.y).coerceIn(-maxUp, 0f)
                        vx = drag.x / dt * 0.6f; vy = drag.y / dt * 0.6f
                    }
                }
        ) {
            DripView(vm.dripState, vm.dripRain, 78.dp, Modifier, accent = vm.accent, calm = vm.calm, squash = squash, spin = spin.value, lookX = vm.dripLook)
        }
    }
}

// ------------------------------------------------------------------ role chooser
@Composable
fun RoleScreen(vm: AppVm) {
    var showPw by rememberSaveable { mutableStateOf(vm.devAsk) }
    var pw by rememberSaveable { mutableStateOf("") }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(22.dp), verticalArrangement = Arrangement.spacedBy(22.dp)) {
        Spacer(Modifier.height(8.dp))
        T("Welcome to FlowBeacon", size = 21, bold = true)
        Sub("Choose how you will use the app. You can switch later from the top bar.")
        listOf("consumer" to "devices", "team" to "team", "dev" to "lock").forEach { (r, ic) ->
            Column(
                Modifier.fillMaxWidth().neu("card").clip(RoundedCornerShape(18.dp)).clickable { if (r == "dev") showPw = true else vm.chooseRole(r) }.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Ico(ic, 40.dp)
                T(Roles.NAME.getValue(r), size = 16, bold = true, color = FB.AC)
                Sub(Roles.DESC.getValue(r))
            }
        }
        if (showPw) {
            NeuCard(title = "Developer password") {
                NeuField(pw, { pw = it }, password = true, keyboard = KeyboardOptions(keyboardType = KeyboardType.Password), onDone = { vm.tryDev(pw) })
                if (vm.devMsg.isNotEmpty()) T(vm.devMsg, size = 12, color = Color(0xFFEF4444))
                NeuButton("Unlock", { vm.tryDev(pw) }, main = true)
            }
        }
        if (vm.chooserCancel) NeuButton("Cancel", { vm.cancelChooser() })
    }
}

// ------------------------------------------------------------------ Overview
@Composable
fun OverviewPage(vm: AppVm) {
    val s = vm.snap
    NeuCard {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Orb(if (s != null) Color(s.level.color) else FB.MU)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                if (s == null) {
                    T("Waiting for data", size = 24, bold = true, color = FB.TX)
                    Sub("Connect the board or start demo mode.")
                } else {
                    val c = Color(s.level.color)
                    T(s.level.icon + " " + s.level.name, size = 24, bold = true, color = c)
                    Sub(s.e.cause)
                    Sub(if (s.e.ev.isNotEmpty()) s.e.ev.joinToString(" · ") else if (vm.base != null) "Readings match baseline" else "Set a baseline while flow is normal")
                    if (s.pred.isNotEmpty()) Sub(s.pred, color = FB.AC)
                    if (s.ml.isNotEmpty()) Sub(s.ml)
                    Sub(if (s.issues.isNotEmpty()) "Sensor check: " + s.issues.joinToString("; ") else "Sensors look healthy", color = if (s.issues.isNotEmpty()) Color(0xFFE8761F) else FB.MU)
                }
            }
        }
        if (s != null && s.e.lvl > 0) Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Pill("Severity: " + s.level.sev, Color(s.level.color)); Pill("Confidence: ${s.e.conf}% (estimate)", FB.AC)
        }
        if (vm.msg.isNotEmpty()) Sub(vm.msg)
        if (vm.demo) {
            Sub("Demo scenario:")
            Box(Modifier.horizontalScroll(rememberScrollState()).padding(vertical = 12.dp)) {
                Seg(AppVm.SCEN_NAMES.toList(), vm.scen, { vm.setScenario(it) })
            }
        }
    }
    NeuCard(title = "Drains") {
        val st = if (s != null) s.level.icon + " " + s.level.name else "No data"
        Row(Modifier.padding(vertical = 8.dp).widthIn(min = 200.dp).neu("card").padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(11.dp).clip(RoundedCornerShape(50)).background(if (s != null) Color(s.level.color) else FB.MU))
            Column(Modifier.padding(start = 10.dp)) { T(vm.node, size = 14, bold = true, maxLines = 1); Sub(st) }
        }
        var name by rememberSaveable { mutableStateOf(vm.node) }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) { NeuField(name, { name = it }) }
            NeuButton("Rename", { vm.renameNode(name) })
        }
        vm.otherNames().forEach { (n, lvl) -> Sub(n + " · " + Core.LEVELS[lvl].icon + " " + Core.LEVELS[lvl].name) }
    }
    val d = s?.d; val b = vm.base
    Row(horizontalArrangement = Arrangement.spacedBy(22.dp)) {
        Kpi("Water flow", d?.let { String.format(Locale.US, "%.2f", it.flow) } ?: "–", "L/min", b?.let { String.format(Locale.US, "Baseline %.2f", it.flow) } ?: "Baseline not set", Modifier.weight(1f))
        Kpi("Distance to water", d?.let { String.format(Locale.US, "%.1f", it.dist) } ?: "–", "cm", b?.let { String.format(Locale.US, "Baseline %.1f cm", it.dist) } ?: "Baseline not set", Modifier.weight(1f))
    }
    Row(horizontalArrangement = Arrangement.spacedBy(22.dp)) {
        Kpi("Turbidity", d?.turb?.roundToInt()?.toString() ?: "–", "units", b?.let { "Baseline " + it.turb.roundToInt() } ?: "Baseline not set", Modifier.weight(1f))
        Kpi("Rain plate", if (d == null) "–" else if (d.rain) "Wet" else "Dry", "", "Wet or dry only", Modifier.weight(1f))
    }
}

@Composable
fun Kpi(title: String, value: String, unit: String, base: String, modifier: Modifier) {
    val ac = FB.AC
    Box(modifier.neu("card").clip(RoundedCornerShape(18.dp))) {
        Column(Modifier.padding(start = 16.dp, end = 12.dp, top = 14.dp, bottom = 18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(8.dp).clip(RoundedCornerShape(50)).background(ac))
                T(title.uppercase(), Modifier.padding(start = 8.dp), 10, true, FB.MU, spacing = 1f, maxLines = 2)
            }
            Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                T(value, size = 28, bold = true, maxLines = 1)
                if (unit.isNotEmpty()) Sub(unit)
            }
            Sub(base)
        }
        Box(Modifier.align(Alignment.BottomStart).fillMaxWidth().height(3.dp).background(Brush.horizontalGradient(0f to ac.copy(alpha = 0.7f), 0.7f to Color.Transparent, 1f to Color.Transparent)))
    }
}

// ------------------------------------------------------------------ Drain model
@Composable
fun ModelPage(vm: AppVm) {
    var win by rememberSaveable { mutableStateOf("90") }
    NeuCard(title = "Drain model") { Inset(pad = 0.dp) { DrainPicture(vm) } }
    NeuCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            H2("Trend", Modifier.weight(1f))
            Box(Modifier.width(150.dp)) { NeuSelect(listOf("90" to "Last 90", "300" to "Last 300", "900" to "Last 900"), win, { win = it }) }
        }
        Inset(pad = 8.dp) { LineChart(vm, win.toInt()) }
        Row { T("Flow", size = 12, color = FB.AC); T(" and water level", size = 12) }
    }
}

@Composable
fun LineChart(vm: AppVm, win: Int) {
    val ver = vm.histVer
    val ac = FB.AC; val tx = FB.TX
    Canvas(Modifier.fillMaxWidth().height(190.dp)) {
        val v = vm.hist.takeLast(win)
        if (v.size < 2 || ver < 0) return@Canvas
        fun line(sel: (Sample) -> Double, col: Color, inv: Boolean) {
            val a = v.map(sel)
            val mn = a.min(); var mx = a.max()
            if (mx - mn < 0.5) mx = mn + 0.5
            val p = Path()
            a.forEachIndexed { i, y ->
                val x = i.toFloat() / (a.size - 1) * (size.width - 24f) + 12f
                val q = ((y - mn) / (mx - mn)).toFloat()
                val py = (if (inv) q else 1f - q) * (size.height - 40f) + 20f
                if (i == 0) p.moveTo(x, py) else p.lineTo(x, py)
            }
            drawPath(p, col, style = Stroke(width = 2.5.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round))
        }
        line({ it.f }, ac, false)
        line({ it.l }, tx, true)
    }
}

// ------------------------------------------------------------------ Incidents
@Composable
fun IncidentsPage(vm: AppVm) {
    val ctx = LocalContext.current
    var min by rememberSaveable { mutableStateOf("0") }
    var confirm by rememberSaveable { mutableStateOf(false) }
    var label by rememberSaveable { mutableStateOf("normal") }
    NeuCard {
        H2("Incident reports")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) { NeuSelect(listOf("0" to "All", "2" to "Warning+", "3" to "Risk+"), min, { min = it }) }
            NeuButton("CSV", {
                val i = Intent(Intent.ACTION_SEND).apply { type = "text/plain"; putExtra(Intent.EXTRA_SUBJECT, "FlowBeacon incidents"); putExtra(Intent.EXTRA_TEXT, vm.csv()) }
                ctx.startActivity(Intent.createChooser(i, "Share incidents"))
            })
            if (confirm) NeuButton("Sure?", { vm.clearIncidents(); confirm = false }, main = true) else NeuButton("Clear", { confirm = true })
        }
        Inset(pad = 10.dp) {
            val list = vm.incidents.filter { it.lvl >= min.toInt() }
            if (list.isEmpty()) Sub("No incidents recorded.", Modifier.padding(8.dp))
            list.take(60).forEach { i ->
                val c = Color(i.color)
                Row(Modifier.padding(vertical = 5.dp).fillMaxWidth().height(IntrinsicSize.Min)) {
                    Box(Modifier.width(6.dp).fillMaxHeight().clip(RoundedCornerShape(3.dp)).background(c))
                    Column(Modifier.padding(start = 10.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        T(vm.node + " · " + i.cond, size = 13, bold = true, color = c)
                        T("${i.sev} severity, ${i.conf}% confidence", size = 12)
                        Sub(i.cause)
                        if (i.ev.isNotEmpty()) Sub(i.ev)
                        Sub(i.time)
                    }
                }
            }
        }
    }
    NeuCard(title = "Test recording") {
        FieldLabel("Label for this session")
        NeuSelect(listOf("normal", "partial valve", "heavy valve", "rain", "overflow").map { it to it }, label, { label = it })
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            NeuButton(if (vm.recording) "Stop recording" else "Start recording", { vm.toggleRecording() }, main = vm.recording)
            NeuButton("Share CSV", {
                val i = Intent(Intent.ACTION_SEND).apply { type = "text/plain"; putExtra(Intent.EXTRA_SUBJECT, "FlowBeacon recording: $label"); putExtra(Intent.EXTRA_TEXT, vm.recCsv(label)) }
                ctx.startActivity(Intent.createChooser(i, "Share recording"))
            })
        }
        Sub(if (vm.recCount > 0) "${vm.recCount} rows" else "Saved files are labelled data you can use later to train a TinyML model.")
        Spacer(Modifier.height(6.dp))
        H2("Calibration wizard")
        val done = vm.wzStep >= WZ_STEPS.size
        Sub(when {
            !vm.wzOn -> "Press Calibration to start."
            done -> vm.wzSug?.let { "Done. Suggested: flow drop ${it.dropWarn.roundToInt()}% / ${it.dropBlock.roundToInt()}%, level rise ${it.rise} cm." } ?: "Done."
            vm.wzRecording -> "Recording step ${vm.wzStep + 1}… keep conditions steady for 10 readings."
            else -> "Step ${vm.wzStep + 1} of 4: ${WZ_STEPS[vm.wzStep]}. Set it up, then record."
        })
        if (vm.wzOn && !done) NeuButton("Record step", { vm.wizardRecord() })
        if (vm.wzOn && done) NeuButton("Apply thresholds", { vm.wizardApply() })
    }
}

// ------------------------------------------------------------------ Connection
@Composable
fun ConnectPage(vm: AppVm) {
    var ip by rememberSaveable { mutableStateOf(vm.ip) }
    NeuCard(title = "Connection") {
        FieldLabel("Board address (IP)")
        NeuField(ip, { ip = it }, placeholder = "192.168.1.45", keyboard = KeyboardOptions(keyboardType = KeyboardType.Uri))
        if (vm.wsOn) NeuButton("Disconnect", { vm.stopAll() }) else NeuButton("Connect", { vm.connectWs(ip) }, main = true)
        Sub("The phone and the board must be on the same Wi-Fi. To give the board its Wi-Fi details, use the desktop app over USB; the board then shows its address.")
        if (vm.msg.isNotEmpty()) Sub(vm.msg)
    }
    UsbCard(vm)
    NeuCard(title = "SMS alerts") {
        Sub("SMS is sent by the board. The Arduino Nano sketch has no GSM module, so this does nothing until you add one.")
        Row(verticalAlignment = Alignment.CenterVertically) {
            T("Send SMS alerts", Modifier.weight(1f))
            NeuSwitch(vm.smsOn, { vm.smsOn = it; vm.saveSms() })
        }
        FieldLabel("Mobile numbers (separate with commas)")
        NeuField(vm.smsNums, { vm.smsNums = it; vm.saveSms() }, placeholder = "+91 98765 43210", keyboard = KeyboardOptions(keyboardType = KeyboardType.Phone))
        FieldLabel("Send when")
        NeuSelect(listOf("2" to "Blockage warning or worse", "3" to "Overflow risk or worse", "4" to "Overflow detected only"), vm.smsMin.toString(), { vm.smsMin = it.toInt(); vm.saveSms() })
        FieldLabel("Wait between SMS")
        NeuSelect(listOf("1" to "1 minute", "5" to "5 minutes", "10" to "10 minutes", "30" to "30 minutes"), vm.smsCool.toString(), { vm.smsCool = it.toInt(); vm.saveSms() })
        NeuButton("Send test SMS", { vm.testSms() })
        if (vm.smsLog.isNotEmpty()) Inset(pad = 10.dp) { Sub(vm.smsLog) }
    }
}

// ------------------------------------------------------------------ Calibration
private val DIALS = listOf(
    Triple("dropWarn", "Flow drop: possible (%)", doubleArrayOf(5.0, 90.0, 1.0)),
    Triple("dropBlock", "Flow drop: blockage (%)", doubleArrayOf(10.0, 95.0, 1.0)),
    Triple("rise", "Level rise warning (cm)", doubleArrayOf(0.2, 5.0, 0.1)),
    Triple("risk", "Overflow risk distance (cm)", doubleArrayOf(1.0, 20.0, 0.5)),
    Triple("over", "Overflow distance (cm)", doubleArrayOf(0.5, 10.0, 0.5)),
    Triple("turb", "Turbidity change (%)", doubleArrayOf(5.0, 100.0, 1.0))
)

private fun Cfg.get(k: String) = when (k) { "dropWarn" -> dropWarn; "dropBlock" -> dropBlock; "rise" -> rise; "risk" -> risk; "over" -> over; else -> turb }
private fun Cfg.with(k: String, v: Double) = when (k) {
    "dropWarn" -> copy(dropWarn = v); "dropBlock" -> copy(dropBlock = v); "rise" -> copy(rise = v)
    "risk" -> copy(risk = v); "over" -> copy(over = v); else -> copy(turb = v)
}

@Composable
fun CalibPage(vm: AppVm) {
    NeuCard(title = "Calibration dials", pad = PaddingValues(horizontal = 12.dp, vertical = 18.dp)) {
        DIALS.chunked(2).forEach { pair ->
            Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), horizontalArrangement = Arrangement.SpaceEvenly) {
                pair.forEach { (k, label, r) ->
                    Column(Modifier.width(140.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Knob(vm.cfg.get(k), r[0], r[1], r[2], { v -> vm.updateCfg(vm.cfg.with(k, v)) })
                        val v = vm.cfg.get(k)
                        T((if (v % 1.0 == 0.0) v.toInt().toString() else v.toString()) + " " + (if (label.contains("(%)")) "%" else "cm"), size = 15, bold = true, align = TextAlign.Center)
                        T(label.uppercase(), Modifier.fillMaxWidth().padding(horizontal = 4.dp), 11, true, FB.MU, TextAlign.Center, 0.7f)
                    }
                }
            }
        }
        NeuButton("Reset thresholds", { vm.resetCfg() })
        Sub("Turn a dial by dragging it. The level sensor has three probes, so the water reads 15 cm (dry), 11 (low probe), 7 (mid probe) or 3 cm (high probe): Overflow risk 7 = mid probe, Overflow 3 = high probe. Tune them with normal-flow readings and partial-valve tests. Everything is saved automatically.")
    }
    LearnCards(vm)
}

// ------------------------------------------------------------------ Ask Drip
@Composable
fun DripPage(vm: AppVm) {
    val chat = remember { mutableStateListOf<Pair<Boolean, String>>(false to DripChat.HELP) }
    var input by rememberSaveable { mutableStateOf("") }
    fun ask() {
        val t = input.trim()
        if (t.isEmpty()) return
        input = ""
        val r = DripChat.reply(t, vm.chatCtx())
        chat.add(true to t); chat.add(false to r.text)
        vm.say(r.text, 7000)
        vm.act(r.action)
    }
    NeuCard(title = "Ask Drip") {
        Sub("Drip answers offline. Try: status, why, when will it overflow, tip, help.")
        Inset(pad = 12.dp) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                chat.forEach { (me, text) ->
                    Row(Modifier.fillMaxWidth()) {
                        T(if (me) "You: " else "Drip: ", size = 13, bold = true, color = if (me) FB.MU else FB.AC)
                        T(text, Modifier.weight(1f), 13)
                    }
                }
            }
        }
        NeuField(input, { input = it }, placeholder = "Ask Drip…", onDone = { ask() })
        NeuButton("Ask", { ask() }, main = true)
    }
}

// ------------------------------------------------------------------ Settings
@Composable
fun SettingsPage(vm: AppVm) {
    NeuCard(title = "Appearance and behaviour") {
        FieldLabel("Theme colour")
        Row(Modifier.horizontalScroll(rememberScrollState()).padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Palettes.ACCENTS.forEach { (k, _, c) -> Swatch(Color(c), vm.accent == k) { vm.updateAccent(k) } }
        }
        FieldLabel("Mode")
        NeuSelect(listOf("light" to "Light", "dark" to "Dark", "auto" to "Follow system"), vm.mode, { vm.setModeTo(it) })
        Row(Modifier.padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            T("Reduce motion", Modifier.weight(1f)); NeuSwitch(vm.calm, { vm.setCalmOn(it) })
        }
    }
    NeuCard(title = "Alerts") {
        listOf("ui" to "Interface sounds", "possible" to "Possible blockage", "warning" to "Blockage warning", "risk" to "Overflow risk", "overflow" to "Overflow", "rain" to "Rain", "predict" to "Prediction").forEach { (k, name) ->
            Row(Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                T(name, Modifier.weight(1f)); NeuSwitch(vm.sndOn(k), { vm.setSndOn(k, it) })
            }
        }
        Row(Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
            T("Vibrate on overflow risk", Modifier.weight(1f)); NeuSwitch(vm.vibrate, { vm.setVibrateOn(it) })
        }
    }
    SettingsExtras(vm)
    NeuCard(title = "About") {
        T("FlowBeacon 2.0.5")
        Sub("by TechMinds. Smart drainage monitoring and blockage prediction for the Arduino Nano prototype.")
        Sub("Switch between Consumer, Maintenance and Developer modes with the button in the top bar.")
    }
}

// ------------------------------------------------------------------ Console
@Composable
fun ConsolePage(vm: AppVm) {
    var cmd by rememberSaveable { mutableStateOf("") }
    var pw by rememberSaveable { mutableStateOf("") }
    var pwMsg by rememberSaveable { mutableStateOf("") }
    NeuCard(title = "Developer access") {
        NeuField(pw, { pw = it }, password = true, placeholder = "At least 4 characters")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            NeuButton("Save", { pwMsg = vm.changeDevPw(pw); if (pwMsg.startsWith("Password")) pw = "" })
            NeuButton("Reset to 1234", { pwMsg = vm.resetDevPw() })
        }
        if (pwMsg.isNotEmpty()) Sub(pwMsg)
    }
    NeuCard(title = "Firmware console") {
        Inset(Modifier.heightIn(min = 180.dp, max = 320.dp), pad = 10.dp) {
            Column(Modifier.verticalScroll(rememberScrollState(), reverseScrolling = true)) { vm.raw.takeLast(80).forEach { T(it, size = 11) } }
        }
        NeuField(cmd, { cmd = it }, placeholder = "Command to send, e.g. restart", onDone = { vm.sendConsole(cmd); cmd = "" })
        NeuButton("Send", { vm.sendConsole(cmd); cmd = "" })
        Sub("Send one JSON line per second: {\"flow\":4.2,\"dist\":12.5,\"turb\":850,\"rain\":0}  flow = L/min, dist = cm to water, turb = higher means dirtier, rain = 1 wet / 0 dry.")
    }
}
