package com.techminds.flowbeacon

import android.content.Context
import android.content.Intent
import android.graphics.Paint
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.roundToInt

private fun share(ctx: Context, subject: String, text: String) {
    val i = Intent(Intent.ACTION_SEND).apply { type = "text/plain"; putExtra(Intent.EXTRA_SUBJECT, subject); putExtra(Intent.EXTRA_TEXT, text) }
    ctx.startActivity(Intent.createChooser(i, subject))
}

private fun fileName(ctx: Context, uri: Uri): String {
    try {
        ctx.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) return c.getString(0).substringBeforeLast('.')
        }
    } catch (e: Exception) { }
    return "recording"
}

private fun readCsv(ctx: Context, uri: Uri): List<CsvRow> = try {
    val text = ctx.contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() } ?: ""
    Ml.parseCsv(text, fileName(ctx, uri))
} catch (e: Exception) { emptyList() }

// ------------------------------------------------------------------ update bar
@Composable
fun UpdateBar(vm: AppVm) {
    val u = vm.upd ?: return
    val ctx = LocalContext.current
    NeuCard(Modifier.padding(horizontal = 18.dp, vertical = 6.dp), pad = androidx.compose.foundation.layout.PaddingValues(14.dp)) {
        T("FlowBeacon ${u.latest} is available (you have ${u.current}).", size = 12, bold = true)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            NeuButton("Download", { ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(u.url))) }, main = true)
            NeuButton("Later", { vm.upd = null })
        }
    }
}

// ------------------------------------------------------------------ History
@Composable
fun HistoryPage(vm: AppVm) {
    val ctx = LocalContext.current
    var node by rememberSaveable { mutableStateOf("drain-1") }
    var days by rememberSaveable { mutableStateOf("1") }
    var tick by remember { mutableStateOf(0) }
    val nodes = vm.nodeList()
    val rows = remember(node, days, tick) { val now = System.currentTimeMillis(); vm.history.range(node, now - days.toInt() * 86400000L, now) }
    val list = remember(rows) { HistCalc.group(rows, days.toInt()) }
    val ac = FB.AC; val tx = FB.TX
    NeuCard {
        H2("History")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) { NeuSelect(nodes, node, { node = it }) }
            Box(Modifier.weight(1f)) { NeuSelect(listOf("1" to "24 hours", "7" to "7 days", "30" to "30 days"), days, { days = it }) }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            NeuButton("Refresh", { tick++ })
            NeuButton("Export CSV", { share(ctx, "FlowBeacon history", HistCalc.csv(rows)) })
        }
        Inset(pad = 8.dp) {
            Canvas(Modifier.fillMaxWidth().height(200.dp)) {
                if (list.size < 2) return@Canvas
                fun line(sel: (HGroup) -> Double, col: Color, inv: Boolean) {
                    val a = list.map(sel)
                    val mn = a.min(); var mx = a.max()
                    if (mx - mn < 0.5) mx = mn + 0.5
                    val p = Path()
                    a.forEachIndexed { i, y ->
                        val x = i.toFloat() / (a.size - 1) * (size.width - 20f) + 10f
                        val q = ((y - mn) / (mx - mn)).toFloat()
                        val py = (if (inv) q else 1f - q) * (size.height - 44f) + 12f
                        if (i == 0) p.moveTo(x, py) else p.lineTo(x, py)
                    }
                    drawPath(p, col, style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round))
                }
                line({ it.f }, ac, false)
                line({ it.l }, tx, true)
                list.forEachIndexed { i, g ->
                    val x = i.toFloat() / (list.size - 1) * (size.width - 20f) + 10f
                    drawRect(Color(Core.LEVELS[g.lvl].color), Offset(x - 3f, size.height - 18f), androidx.compose.ui.geometry.Size(6f, 10f))
                }
            }
            if (list.size < 2) Sub("No history yet. Readings are stored every minute while the app runs.", Modifier.padding(8.dp))
        }
        Sub("Flow (accent) and water level (dark). The coloured marks at the bottom show the worst condition of each period.")
    }
    NeuCard(title = if (days == "1") "Hour" else "Day") {
        val f = SimpleDateFormat(if (days == "1") "HH:mm" else "yyyy-MM-dd", Locale.US)
        list.takeLast(14).reversed().forEach { g ->
            val lv = Core.LEVELS[g.lvl]
            Column(Modifier.padding(vertical = 4.dp)) {
                T(f.format(Date(g.t)) + " · " + g.n + " min", size = 12, bold = true)
                Sub(String.format(Locale.US, "Avg flow %.2f · level %.1f / %.1f cm", g.f, g.lmin, g.lmax))
                T(lv.icon + " " + lv.name, size = 12, color = Color(lv.color))
            }
        }
        if (list.isEmpty()) Sub("Nothing stored for this period.")
    }
}

// ------------------------------------------------------------------ City map
private fun project(states: List<DevState>, w: Float, h: Float, pad: Float = 40f): Map<String, Offset> {
    if (states.isEmpty()) return emptyMap()
    val la = states.map { it.dv.lat }; val lo = states.map { it.dv.lng }
    val dla = maxOf(la.max() - la.min(), 0.004); val dlo = maxOf(lo.max() - lo.min(), 0.004)
    val sc = minOf((w - 2 * pad) / dlo, (h - 2 * pad) / dla)
    val cx = (lo.min() + lo.max()) / 2; val cy = (la.min() + la.max()) / 2
    return states.associate { it.id to Offset((w / 2 + (it.dv.lng - cx) * sc).toFloat(), (h / 2 - (it.dv.lat - cy) * sc).toFloat()) }
}

@Composable
fun MapCanvas(states: List<DevState>, sel: String?, label: (DevState) -> String, onPick: (String) -> Unit) {
    val sd = FB.SD; val ac = FB.AC; val tx = FB.TX
    val paint = remember { Paint().apply { isAntiAlias = true; textAlign = Paint.Align.CENTER } }
    Canvas(
        Modifier.fillMaxWidth().height(300.dp).pointerInput(states) {
            detectTapGestures { o ->
                val pos = project(states, size.width.toFloat(), size.height.toFloat())
                val best = pos.minByOrNull { (it.value - o).getDistance() }
                if (best != null && (best.value - o).getDistance() < 48.dp.toPx()) onPick(best.key)
            }
        }
    ) {
        val w = size.width; val h = size.height
        for (i in 1..7) drawLine(sd, Offset(w * i / 8, 0f), Offset(w * i / 8, h), 1f)       // a plain grid instead of map tiles: works offline
        for (i in 1..5) drawLine(sd, Offset(0f, h * i / 6), Offset(w, h * i / 6), 1f)
        val pos = project(states, w, h)
        paint.color = tx.toArgb(); paint.textSize = 11.dp.toPx()
        states.forEach { s ->
            val p = pos[s.id] ?: return@forEach
            if (s.id == sel) drawCircle(ac, 17.dp.toPx(), p, style = Stroke(3.dp.toPx()))
            drawCircle(Color(CityBook.STAT_COLOR.getValue(s.status)), 11.dp.toPx(), p)
            drawContext.canvas.nativeCanvas.drawText(label(s), p.x, p.y + 28.dp.toPx(), paint)
        }
    }
}

@Composable
fun CityMapPage(vm: AppVm) {
    val city = vm.city
    var rev by remember { mutableStateOf(0) }
    var tick by remember { mutableStateOf(0) }
    var sel by rememberSaveable { mutableStateOf("") }
    var ward by rememberSaveable { mutableStateOf("") }
    var zone by rememberSaveable { mutableStateOf("") }
    var stat by rememberSaveable { mutableStateOf("") }
    var team by rememberSaveable { mutableStateOf("") }
    var msg by remember { mutableStateOf("") }
    var pinIn by rememberSaveable { mutableStateOf("") }
    var pinNew by rememberSaveable { mutableStateOf("") }
    var newTeam by rememberSaveable { mutableStateOf("") }
    var newId by rememberSaveable { mutableStateOf("") }
    var officer by rememberSaveable { mutableStateOf(city.officer) }
    var eName by rememberSaveable { mutableStateOf("") }
    var eWard by rememberSaveable { mutableStateOf("") }
    var eZone by rememberSaveable { mutableStateOf("") }
    var eLat by rememberSaveable { mutableStateOf("") }
    var eLng by rememberSaveable { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    LaunchedEffect(Unit) { while (true) { delay(3000); tick++ } }

    if (rev < 0) return                       // reads rev so every action below refreshes the page
    if (city.locked) {
        NeuCard(title = "City map is locked") {
            NeuField(pinIn, { pinIn = it }, placeholder = "Officials PIN", password = true, onDone = { if (city.tryUnlock(pinIn)) { pinIn = ""; msg = ""; rev++ } else { msg = "Wrong PIN." } })
            NeuButton("Unlock", { if (city.tryUnlock(pinIn)) { pinIn = ""; msg = ""; rev++ } else { msg = "Wrong PIN." } }, main = true)
            if (msg.isNotEmpty()) Sub(msg)
        }
        return
    }
    val all = remember(vm.nodesVer, vm.cityVer, tick, rev, vm.snap) { city.states(vm.liveNodes()) }
    val wards = all.map { it.dv.ward.ifEmpty { "Unassigned" } }.distinct().sorted()
    val zones = all.map { it.dv.zone.ifEmpty { "Unassigned" } }.distinct().sorted()
    val st = all.filter {
        (ward.isEmpty() || (it.dv.ward.ifEmpty { "Unassigned" }) == ward) && (zone.isEmpty() || (it.dv.zone.ifEmpty { "Unassigned" }) == zone) &&
            (stat.isEmpty() || it.status == stat)
    }
    val cur = all.firstOrNull { it.id == sel }
    val ids = st.map { it.id }.toSet()
    val incs = city.incidents.filter { it.dev in ids }
    val f = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US)
    fun pick(id: String) {
        sel = id
        city.devices[id]?.let { eName = it.name; eWard = it.ward; eZone = it.zone; eLat = it.lat.toString(); eLng = it.lng.toString() }
    }

    NeuCard {
        H2("City map")
        NeuSelect(listOf("" to "All wards") + wards.map { it to it }, ward, { ward = it })
        NeuSelect(listOf("" to "All zones") + zones.map { it to it }, zone, { zone = it })
        NeuSelect(listOf("" to "All statuses") + CityBook.STAT.map { it.key to it.value }, stat, { stat = it })
        Inset(pad = 6.dp) { MapCanvas(st, sel.ifEmpty { null }, { city.label(it) }, { pick(it) }) }
        Sub("${st.size} drains · ${st.count { it.online }} online · ${incs.count { it.status != "resolved" }} open incidents")
        Sub("A schematic map: pins are placed from each drain's latitude and longitude, so it works without internet.")
    }

    NeuCard(title = "Selected drain") {
        if (cur == null) Sub("Select a pin on the map or a row in the list.") else {
            val l = cur.last; val inc = city.openInc(cur.id)
            T(city.label(cur) + " · " + (CityBook.STAT[cur.status] ?: ""), size = 14, bold = true, color = Color(CityBook.STAT_COLOR.getValue(cur.status)))
            if (l != null) {
                val b = cur.base
                Sub(String.format(Locale.US, "Flow %.2f L/min · level %.1f cm", l.flow, l.dist) + (if (b != null) String.format(Locale.US, " (%+.1f vs baseline)", b.dist - l.dist) else ""))
            }
            if (inc != null) {
                Sub("Incident: " + (CityBook.INC_ST[inc.status] ?: "") + (if (inc.team.isNotEmpty()) " · " + inc.team else ""))
                inc.log.takeLast(4).forEach { Sub(SimpleDateFormat("MM-dd HH:mm", Locale.US).format(Date(it.t)) + "  " + it.m) }
            }
            NeuSelect(city.teams.map { it to it }, team.ifEmpty { city.teams.firstOrNull() ?: "" }, { team = it })
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                NeuButton("Assign", { msg = city.assign(cur.id, team.ifEmpty { city.teams.firstOrNull() ?: "" }, cur.lvl); city.save(); rev++ }, main = true)
                NeuButton("Start work", { city.startWork(cur.id); city.save(); rev++ })
                if (confirm == cur.id) NeuButton("Sure?", { city.resolve(cur.id); city.save(); confirm = ""; rev++ }, main = true)
                else NeuButton("Mark resolved", { confirm = cur.id })
            }
            if (msg.isNotEmpty()) Sub(msg)
            FieldLabel("Edit device")
            NeuField(eName, { eName = it }, placeholder = "Name")
            NeuField(eWard, { eWard = it }, placeholder = "Ward")
            NeuField(eZone, { eZone = it }, placeholder = "Zone")
            NeuField(eLat, { eLat = it }, placeholder = "Latitude", keyboard = KeyboardOptions(keyboardType = KeyboardType.Decimal))
            NeuField(eLng, { eLng = it }, placeholder = "Longitude", keyboard = KeyboardOptions(keyboardType = KeyboardType.Decimal))
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                NeuButton("Save", {
                    msg = if (city.editDevice(cur.id, eName, eWard, eZone, eLat.toDoubleOrNull(), eLng.toDoubleOrNull())) "" else "Enter a valid latitude and longitude."
                    city.save(); rev++
                })
                NeuButton("Remove from map", { city.hide.add(cur.id); sel = ""; city.save(); rev++ })
            }
        }
    }

    NeuCard(title = "Drains and incidents") {
        st.forEach { s ->
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).clickable { pick(s.id) }.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.width(10.dp).height(10.dp).clip(RoundedCornerShape(50)).background(Color(CityBook.STAT_COLOR.getValue(s.status))))
                Column(Modifier.padding(start = 10.dp)) {
                    T(city.label(s), size = 13, bold = true)
                    Sub((s.dv.ward.ifEmpty { "Unassigned" }) + " · " + (s.dv.zone.ifEmpty { "Unassigned" }) + " · " + (CityBook.STAT[s.status] ?: ""))
                }
            }
        }
        if (st.isEmpty()) Sub("No drains to show yet.")
        FieldLabel("Incidents")
        incs.take(40).forEach { i ->
            val d = all.firstOrNull { it.id == i.dev }
            Sub(f.format(Date(i.start)) + " · " + (if (d != null) city.label(d) else i.dev) + " · " + CityBook.LVLN[i.max] + " · " + (CityBook.INC_ST[i.status] ?: "") + (if (i.team.isNotEmpty()) " · " + i.team else ""))
        }
        if (incs.isEmpty()) Sub("No incidents recorded.")
    }

    NeuCard(title = "Teams, officials and devices") {
        FieldLabel("Officer name")
        NeuField(officer, { officer = it; city.officer = it.trim(); city.save() }, placeholder = "Your name (kept in the incident log)")
        Sub("Teams: " + city.teams.joinToString(", "))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) { NeuField(newTeam, { newTeam = it }, placeholder = "New team name") }
            NeuButton("Add team", { if (city.addTeam(newTeam)) { newTeam = ""; city.save(); rev++ } })
        }
        city.teams.forEachIndexed { i, t -> Row(verticalAlignment = Alignment.CenterVertically) { T(t, Modifier.weight(1f)); NeuButton("Remove", { city.removeTeam(i); city.save(); rev++ }) } }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) { NeuField(newId, { newId = it }, placeholder = "New device id") }
            NeuButton("Add device", { city.addDevice(newId)?.let { id -> newId = ""; city.save(); pick(id); rev++ } })
        }
        NeuField(pinNew, { pinNew = it }, placeholder = "New PIN (at least 4 characters)", password = true)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            NeuButton("Set PIN", { msg = city.setPin(pinNew); pinNew = ""; city.save(); rev++ })
            NeuButton("Remove PIN", { msg = city.clearPin(); city.save(); rev++ })
        }
        if (msg.isNotEmpty()) Sub(msg)
    }
}

// ------------------------------------------------------------------ Learn, replay, profiles (Calibration tab)
@Composable
fun LearnCards(vm: AppVm) {
    val ctx = LocalContext.current
    var speed by rememberSaveable { mutableStateOf("1") }
    var pname by rememberSaveable { mutableStateOf("") }
    var psel by rememberSaveable { mutableStateOf(0) }
    val pickTrain = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris ->
        vm.loadTraining(uris.flatMap { readCsv(ctx, it) })
    }
    val pickPlay = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) { vm.playRows = readCsv(ctx, uri); vm.replayMsg = if (vm.playRows.isEmpty()) "No readings found in that file." else "${fileName(ctx, uri)}: ${vm.playRows.size} readings" }
    }
    NeuCard(title = "Learn from recordings") {
        Sub("Load the labelled CSV files saved by Test recording (normal, partial valve, rain and so on). Set the baseline first.")
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            NeuButton("Choose CSV files", { pickTrain.launch("*/*") })
            if (vm.trainRows.isNotEmpty()) NeuButton("Train", { vm.trainModel() })
            vm.model?.let { m ->
                NeuButton("Export model.h", { share(ctx, "FlowBeacon model.h", Ml.header(m)) })
                NeuButton("Export JSON", { share(ctx, "FlowBeacon model", m.toJson()) })
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) { T("Use the learned model on the Overview", Modifier.weight(1f)); NeuSwitch(vm.useModel, { vm.setUseModel(it) }) }
        vm.model?.let { if (vm.trainMsg.isEmpty()) Sub("Saved model: " + it.labels.joinToString(", ")) }
        if (vm.trainMsg.isNotEmpty()) Sub(vm.trainMsg)
    }
    NeuCard(title = "Replay a recording") {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            NeuButton("Choose CSV", { pickPlay.launch("*/*") })
            Box(Modifier.width(100.dp)) { NeuSelect(listOf("1" to "1x", "2" to "2x", "5" to "5x", "10" to "10x"), speed, { speed = it }) }
            if (vm.replaying) NeuButton("Stop", { vm.stopReplay() }, main = true)
            else if (vm.playRows.isNotEmpty()) NeuButton("Play", { vm.startReplay(vm.playRows, speed.toInt()) })
        }
        if (vm.replayMsg.isNotEmpty()) Sub(vm.replayMsg)
        H2("Calibration profiles")
        if (vm.profiles.isNotEmpty()) {
            NeuSelect(vm.profiles.mapIndexed { i, p -> i.toString() to p.name }, psel.toString(), { psel = it.toInt() })
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                NeuButton("Apply", { vm.profileApply(psel) })
                NeuButton("Delete", { vm.profileDelete(psel); psel = 0 })
            }
        }
        NeuField(pname, { pname = it }, placeholder = "Profile name")
        NeuButton("Save", { vm.profileSave(pname); pname = "" })
    }
}

// ------------------------------------------------------------------ Language, notifications, quiet hours, updates (Settings tab)
@Composable
fun SettingsExtras(vm: AppVm) {
    NeuCard(title = "Language, notifications and quiet hours") {
        FieldLabel("Language")
        NeuSelect(listOf("en" to "English", "ta" to "தமிழ்"), vm.lang, { vm.setLanguage(it) })
        FieldLabel("Text size")
        NeuSelect(listOf("1.0" to "Normal", "1.15" to "Large", "1.3" to "Extra large"), vm.zoom.toString().let { z -> listOf("1.0", "1.15", "1.3").minByOrNull { Math.abs(it.toFloat() - vm.zoom) } ?: z }, { vm.setZoomTo(it.toFloat()) })
        Row(verticalAlignment = Alignment.CenterVertically) { T("Desktop notifications", Modifier.weight(1f)); NeuSwitch(vm.notifyOn, { vm.setNotifyOn(it) }) }
        Row(verticalAlignment = Alignment.CenterVertically) { T("Keep monitoring in the background", Modifier.weight(1f)); NeuSwitch(vm.bgOn, { vm.setBgOn(it) }) }
        Row(verticalAlignment = Alignment.CenterVertically) { T("Check for updates on start", Modifier.weight(1f)); NeuSwitch(vm.updOn, { vm.setUpdOn(it) }) }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            NeuButton("Check now", { vm.checkUpdates(true) })
            Sub(if (vm.updMsg.isEmpty()) "Version " + Updater.VERSION else vm.updMsg)
        }
        FieldLabel("Quiet hours")
        Row(verticalAlignment = Alignment.CenterVertically) { T("Quiet hours", Modifier.weight(1f)); NeuSwitch(vm.quietOn, { vm.setQuietOn(it) }) }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f)) { NeuField(vm.quietFrom, { vm.setQuietFrom(it) }, placeholder = "22:00", keyboard = KeyboardOptions(keyboardType = KeyboardType.Number)) }
            T("to")
            Box(Modifier.weight(1f)) { NeuField(vm.quietTo, { vm.setQuietTo(it) }, placeholder = "06:00", keyboard = KeyboardOptions(keyboardType = KeyboardType.Number)) }
        }
        FieldLabel("SMS minimum during quiet hours")
        NeuSelect(listOf("2" to "Blockage warning", "3" to "Overflow risk", "4" to "Overflow only"), vm.quietSms.toString(), { vm.setQuietSms(it.toInt()) })
        Sub("During quiet hours there are no sounds or notifications below Overflow risk. Overflow always gets through. Use the 24-hour format, for example 22:00.")
    }
}

// ------------------------------------------------------------------ USB (Connection tab)
@Composable
fun UsbCard(vm: AppVm) {
    NeuCard(title = "USB") {
        Sub("Plug the ESP32-S3 into the phone with a USB OTG cable, then tap Find board. Android asks for permission once.")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            NeuButton("Find board", { vm.refreshUsb() })
        }
        vm.usbLabels.forEachIndexed { i, label ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                T(label, Modifier.weight(1f), 12)
                NeuButton("Connect", { vm.connectUsb(i) }, main = true)
            }
        }
    }
}
