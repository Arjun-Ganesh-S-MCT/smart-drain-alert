package com.techminds.flowbeacon

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.Paint
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
<<<<<<< HEAD
import androidx.compose.ui.geometry.Offset
=======
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
>>>>>>> ce45d4c (2.0.5: fix map clipping, pin icons, my location)
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import kotlin.math.PI
import kotlin.math.atan
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.ln
import kotlin.math.log2
import kotlin.math.pow
import kotlin.math.sinh
import kotlin.math.tan

/** Map tiles from OpenStreetMap (free, no key, no web view). Tiles are saved in the app cache, so seen places still show offline. */
object Tiles {
<<<<<<< HEAD
    const val UA = "FlowBeacon/2.0.3 (+https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert)"
=======
    const val UA = "FlowBeacon/2.0.5 (+https://github.com/Arjun-Ganesh-S-MCT/smart-drain-alert)"
>>>>>>> ce45d4c (2.0.5: fix map clipping, pin icons, my location)
    const val CREDIT = "© OpenStreetMap contributors"
    const val MIN_Z = 2
    const val MAX_Z = 18

    /** Tile units at zoom z (x, y). */
    fun world(lat: Double, lng: Double, z: Int): Pair<Double, Double> {
        val n = 2.0.pow(z)
        val la = lat.coerceIn(-85.0511, 85.0511)
        val x = (lng + 180.0) / 360.0 * n
        val y = (1.0 - ln(tan(Math.toRadians(la)) + 1.0 / cos(Math.toRadians(la))) / PI) / 2.0 * n
        return x to y
    }

    fun unworld(x: Double, y: Double, z: Int): Pair<Double, Double> {
        val n = 2.0.pow(z)
        return Math.toDegrees(atan(sinh(PI * (1.0 - 2.0 * y / n)))) to (x / n * 360.0 - 180.0)
    }

    /** Highest whole zoom at which all points fit in a w x h view (pixels, tile = tilePx), plus the centre. */
    fun fit(points: List<Pair<Double, Double>>, w: Float, h: Float, tilePx: Float): Triple<Float, Double, Double> {
        if (points.isEmpty()) return Triple(12f, CityBook.CENTER_LAT, CityBook.CENTER_LNG)
        val clat = (points.minOf { it.first } + points.maxOf { it.first }) / 2
        val clng = (points.minOf { it.second } + points.maxOf { it.second }) / 2
        for (z in 17 downTo MIN_Z) {
            val xs = points.map { world(it.first, it.second, z) }
            val dx = (xs.maxOf { it.first } - xs.minOf { it.first }) * tilePx
            val dy = (xs.maxOf { it.second } - xs.minOf { it.second }) * tilePx
            if (dx <= w - 120f && dy <= h - 120f) return Triple(z.toFloat(), clat, clng)
        }
        return Triple(MIN_Z.toFloat(), clat, clng)
    }

    private val http = OkHttpClient.Builder().callTimeout(10, TimeUnit.SECONDS).build()
    private val pool = Executors.newFixedThreadPool(3)
    private val mem = object : android.util.LruCache<String, ImageBitmap>(160) {}
    private val busy = ConcurrentHashMap.newKeySet<String>()
    private val failedUntil = ConcurrentHashMap<String, Long>()
    private var dir: File? = null

    /** Bumped when a tile arrives, so the map redraws. */
    var version by mutableStateOf(0)

    fun init(ctx: Context) { if (dir == null) dir = File(ctx.cacheDir, "tiles").also { it.mkdirs() } }

    fun get(z: Int, x: Int, y: Int): ImageBitmap? {
        val n = 1 shl z
        if (y < 0 || y >= n) return null
        val xx = ((x % n) + n) % n
        val key = "$z/$xx/$y"
        mem.get(key)?.let { return it }
        val f = File(dir ?: return null, key.replace('/', '_') + ".png")
        if (f.exists()) {
            val bmp = try { BitmapFactory.decodeFile(f.path)?.asImageBitmap() } catch (e: Exception) { null }
            if (bmp != null) { mem.put(key, bmp); return bmp }
            f.delete()
        }
        if ((failedUntil[key] ?: 0L) > System.currentTimeMillis() || !busy.add(key)) return null
        pool.execute {
            try {
                val req = Request.Builder().url("https://tile.openstreetmap.org/$z/$xx/$y.png").header("User-Agent", UA).build()
                http.newCall(req).execute().use { r ->
                    if (r.isSuccessful) {
                        val bytes = r.body?.bytes()
                        if (bytes != null) { f.writeBytes(bytes); android.os.Handler(android.os.Looper.getMainLooper()).post { version++ } }
                    } else failedUntil[key] = System.currentTimeMillis() + 30000
                }
            } catch (e: Exception) {
                failedUntil[key] = System.currentTimeMillis() + 30000
            } finally {
                busy.remove(key)
            }
        }
        return null
    }
}

<<<<<<< HEAD
/** The map view: drag to move, pinch to zoom, tap a pin to select it. */
class MapView {
=======
/** Finds the phone's position once (last known position first, then a fresh fix from GPS or the network). */
object MyLocation {
    @android.annotation.SuppressLint("MissingPermission")
    fun fetch(ctx: Context, done: (Double, Double) -> Unit, fail: (String) -> Unit) {
        try {
            val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
            val on = listOf(android.location.LocationManager.GPS_PROVIDER, android.location.LocationManager.NETWORK_PROVIDER)
                .filter { try { lm.isProviderEnabled(it) } catch (e: Exception) { false } }
            if (on.isEmpty()) { fail("Turn on location in the phone settings."); return }
            for (p in on) { val l = lm.getLastKnownLocation(p); if (l != null) { done(l.latitude, l.longitude); return } }
            val main = android.os.Handler(android.os.Looper.getMainLooper())
            var finished = false
            val listener = object : android.location.LocationListener {
                override fun onLocationChanged(l: android.location.Location) { if (!finished) { finished = true; lm.removeUpdates(this); done(l.latitude, l.longitude) } }
                @Deprecated("old API") override fun onStatusChanged(provider: String?, status: Int, extras: android.os.Bundle?) { }
                override fun onProviderEnabled(provider: String) { }
                override fun onProviderDisabled(provider: String) { }
            }
            on.forEach { lm.requestLocationUpdates(it, 0L, 0f, listener, android.os.Looper.getMainLooper()) }
            main.postDelayed({ if (!finished) { finished = true; lm.removeUpdates(listener); fail("Could not find your location. Try outside or turn on GPS.") } }, 20000)
        } catch (e: Exception) {
            fail("Could not get your location.")
        }
    }
}

/** The map view: drag to move, pinch to zoom, tap a pin to select it. */
class MapView {
    var meLat by mutableStateOf<Double?>(null)      // the phone's own position (blue dot), once found
    var meLng by mutableStateOf<Double?>(null)
>>>>>>> ce45d4c (2.0.5: fix map clipping, pin icons, my location)
    var zoom by mutableStateOf(12f)
    var lat by mutableStateOf(CityBook.CENTER_LAT)
    var lng by mutableStateOf(CityBook.CENTER_LNG)
    var fitted = false
}

@Composable
fun TileMapView(states: List<DevState>, sel: String?, label: (DevState) -> String, view: MapView, onPick: (String) -> Unit) {
    val ctx = LocalContext.current
    remember { Tiles.init(ctx); 0 }
    val ac = FB.AC; val sd = FB.SD
    val paint = remember { Paint().apply { isAntiAlias = true; textAlign = Paint.Align.CENTER } }
    val credit = remember { Paint().apply { isAntiAlias = true; textAlign = Paint.Align.RIGHT; color = 0xFF333333.toInt() } }
    val ver = Tiles.version                                   // redraw when a tile arrives

    fun toScreen(la: Double, ln: Double, w: Float, h: Float, tilePx: Float): Offset {
        val z = floor(view.zoom).toInt()
        val c = Tiles.world(view.lat, view.lng, z); val p = Tiles.world(la, ln, z)
        val k = tilePx * 2f.pow(view.zoom - z)
        return Offset(w / 2f + ((p.first - c.first) * k).toFloat(), h / 2f + ((p.second - c.second) * k).toFloat())
    }

    Canvas(
<<<<<<< HEAD
        Modifier.fillMaxWidth().height(340.dp)
=======
        Modifier.fillMaxWidth().height(340.dp).clipToBounds()      // tiles must not be drawn outside the map box
>>>>>>> ce45d4c (2.0.5: fix map clipping, pin icons, my location)
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, zoomChange, _ ->
                    view.fitted = true
                    val z = floor(view.zoom).toInt()
                    val k = 256.dp.toPx() * 2f.pow(view.zoom - z)
                    val c = Tiles.world(view.lat, view.lng, z)
                    val n = Tiles.unworld(c.first - pan.x / k, c.second - pan.y / k, z)
                    view.lat = n.first; view.lng = n.second
                    if (zoomChange != 1f) view.zoom = (view.zoom + log2(zoomChange)).coerceIn(Tiles.MIN_Z.toFloat(), Tiles.MAX_Z.toFloat())
                }
            }
            .pointerInput(states) {
                detectTapGestures { o ->
                    val w = size.width.toFloat(); val h = size.height.toFloat()
<<<<<<< HEAD
                    val best = states.map { it.id to toScreen(it.dv.lat, it.dv.lng, w, h, 256.dp.toPx()) }.minByOrNull { (it.second - o).getDistance() }
=======
                    val best = states.map { it.id to (toScreen(it.dv.lat, it.dv.lng, w, h, 256.dp.toPx()) - Offset(0f, 23.dp.toPx())) }.minByOrNull { (it.second - o).getDistance() }
>>>>>>> ce45d4c (2.0.5: fix map clipping, pin icons, my location)
                    if (best != null && (best.second - o).getDistance() < 48.dp.toPx()) onPick(best.first)
                }
            }
    ) {
        if (ver < 0) return@Canvas
        val w = size.width; val h = size.height
        val tilePx = 256.dp.toPx()
        if (!view.fitted && states.isNotEmpty()) {
            val f = Tiles.fit(states.map { it.dv.lat to it.dv.lng }, w, h, tilePx)
            view.zoom = f.first; view.lat = f.second; view.lng = f.third; view.fitted = true
        }
        val z = floor(view.zoom).toInt()
        val k = tilePx * 2f.pow(view.zoom - z)
        val c = Tiles.world(view.lat, view.lng, z)
        val x0 = floor(c.first - w / 2 / k).toInt(); val x1 = floor(c.first + w / 2 / k).toInt()
        val y0 = floor(c.second - h / 2 / k).toInt(); val y1 = floor(c.second + h / 2 / k).toInt()
        drawRect(sd)
        for (ty in y0..y1) for (tx in x0..x1) {
            val left = w / 2 + ((tx - c.first) * k).toFloat(); val top = h / 2 + ((ty - c.second) * k).toFloat()
            val img = Tiles.get(z, tx, ty)
            if (img != null) {
                drawImage(img, dstOffset = IntOffset(Math.round(left), Math.round(top)), dstSize = IntSize(Math.round(k) + 1, Math.round(k) + 1))
            } else {
                drawRect(Color.Gray.copy(alpha = 0.25f), Offset(left, top), Size(k, k), style = Stroke(1f))
            }
        }
        paint.textSize = 11.dp.toPx()
        states.forEach { s ->
            val p = toScreen(s.dv.lat, s.dv.lng, w, h, tilePx)
<<<<<<< HEAD
            if (s.id == sel) { drawCircle(Color.White, 18.dp.toPx(), p, style = Stroke(5.dp.toPx())); drawCircle(ac, 17.dp.toPx(), p, style = Stroke(3.dp.toPx())) }
            drawCircle(Color.White, 12.dp.toPx(), p)
            drawCircle(Color(CityBook.STAT_COLOR.getValue(s.status)), 10.dp.toPx(), p)
=======
            // a map pin: a round head and a point at the exact place
            val r = 11.dp.toPx(); val head = Offset(p.x, p.y - r * 2.1f)
            val col = Color(CityBook.STAT_COLOR.getValue(s.status))
            fun tri(k: Float) = Path().apply {
                moveTo(p.x, p.y + k * 0.6f); lineTo(head.x - (r + k) * 0.85f, head.y + (r + k) * 0.55f); lineTo(head.x + (r + k) * 0.85f, head.y + (r + k) * 0.55f); close()
            }
            if (s.id == sel) drawCircle(ac, r + 6.dp.toPx(), head, style = Stroke(3.dp.toPx()))
            drawPath(tri(2.dp.toPx()), Color.White); drawCircle(Color.White, r + 2.dp.toPx(), head)
            drawPath(tri(0f), col); drawCircle(col, r, head)
            drawCircle(Color.White, r * 0.38f, head)
>>>>>>> ce45d4c (2.0.5: fix map clipping, pin icons, my location)
            val text = label(s)
            val tw = paint.measureText(text) + 12.dp.toPx()
            drawRoundRect(Color.White.copy(alpha = 0.85f), Offset(p.x - tw / 2, p.y + 16.dp.toPx()), Size(tw, 20.dp.toPx()), androidx.compose.ui.geometry.CornerRadius(6.dp.toPx()))
            paint.color = 0xFF222222.toInt()
            drawContext.canvas.nativeCanvas.drawText(text, p.x, p.y + 31.dp.toPx(), paint)
        }
<<<<<<< HEAD
=======
        val ml = view.meLat; val mg = view.meLng
        if (ml != null && mg != null) {                                   // "you are here"
            val q = toScreen(ml, mg, w, h, tilePx)
            drawCircle(Color(0x332F80ED), 24.dp.toPx(), q); drawCircle(Color.White, 9.dp.toPx(), q); drawCircle(Color(0xFF2F80ED), 7.dp.toPx(), q)
        }
>>>>>>> ce45d4c (2.0.5: fix map clipping, pin icons, my location)
        credit.textSize = 10.dp.toPx()
        drawRect(Color.White.copy(alpha = 0.8f), Offset(w - credit.measureText(Tiles.CREDIT) - 12.dp.toPx(), h - 18.dp.toPx()), Size(credit.measureText(Tiles.CREDIT) + 12.dp.toPx(), 18.dp.toPx()))
        drawContext.canvas.nativeCanvas.drawText(Tiles.CREDIT, w - 6.dp.toPx(), h - 5.dp.toPx(), credit)
    }
}
