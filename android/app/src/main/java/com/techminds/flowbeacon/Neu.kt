package com.techminds.flowbeacon

import android.content.Context
import android.graphics.BitmapFactory
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

// ------------------------------------------------------------------ shadow tiles
class TileMeta(val w: Int, val h: Int, val m: Int, val shape: String, val cap: Int)

class TileSet(private val ctx: Context, val key: String) {
    private val imgs = HashMap<String, ImageBitmap>()
    val meta: Map<String, TileMeta> = metaOf(ctx)
    fun img(kind: String): ImageBitmap = imgs.getOrPut(kind) {
        ctx.assets.open("neu/$key/$kind.png").use { BitmapFactory.decodeStream(it).asImageBitmap() }
    }

    companion object {
        private var cached: Map<String, TileMeta>? = null
        fun metaOf(ctx: Context): Map<String, TileMeta> = cached ?: run {
            val o = JSONObject(ctx.assets.open("neu/meta.json").bufferedReader().use { it.readText() })
            val m = HashMap<String, TileMeta>()
            for (k in o.keys()) {
                val t = o.getJSONObject(k)
                m[k] = TileMeta(t.getInt("w"), t.getInt("h"), t.getInt("m"), t.getString("shape"), t.getInt("cap"))
            }
            cached = m; m
        }
    }
}

val LocalTiles = staticCompositionLocalOf<TileSet?> { null }

/** Paints shadow tile [kind] so its body fills (x, y, w, h) in pixels; the soft shadows spill outside, like CSS box-shadow. */
fun DrawScope.drawTile(ts: TileSet, kind: String, x: Float, y: Float, w: Float, h: Float) {
    val m = ts.meta.getValue(kind)
    val img = ts.img(kind)
    val d = density
    val mm = m.m * d
    val tx = x - mm; val ty = y - mm; val tw = w + 2 * mm; val th = h + 2 * mm
    val pw = img.width; val ph = img.height
    fun put(sx: Int, sy: Int, sw: Int, sh: Int, x0: Float, y0: Float, x1: Float, y1: Float) {
        val a = x0.roundToInt(); val b = y0.roundToInt(); val c = x1.roundToInt(); val e = y1.roundToInt()
        if (c <= a || e <= b || sw <= 0 || sh <= 0) return
        drawImage(img, IntOffset(sx, sy), IntSize(sw, sh), IntOffset(a, b), IntSize(c - a, e - b), filterQuality = FilterQuality.Medium)
    }
    if (m.shape == "c" || m.shape == "f") { put(0, 0, pw, ph, tx, ty, tx + m.w * d, ty + m.h * d); return }
    val cs = m.cap * 2
    val capx = min(m.cap * d, tw / 2)
    val xs = floatArrayOf(tx, tx + capx, tx + tw - capx, tx + tw)
    val sx = intArrayOf(0, cs, pw - cs, pw)
    if (m.shape == "h") {
        for (i in 0..2) {
            val s0 = if (i == 1) pw / 2 - 2 else sx[i]
            val s1 = if (i == 1) pw / 2 + 2 else sx[i + 1]
            put(s0, 0, s1 - s0, ph, xs[i], ty, xs[i + 1], ty + th)
        }
        return
    }
    val capy = min(m.cap * d, th / 2)
    val ys = floatArrayOf(ty, ty + capy, ty + th - capy, ty + th)
    val sy = intArrayOf(0, cs, ph - cs, ph)
    for (i in 0..2) for (j in 0..2) {
        val a0 = if (i == 1) pw / 2 - 2 else sx[i]
        val a1 = if (i == 1) pw / 2 + 2 else sx[i + 1]
        val b0 = if (j == 1) ph / 2 - 2 else sy[j]
        val b1 = if (j == 1) ph / 2 + 2 else sy[j + 1]
        put(a0, b0, a1 - a0, b1 - b0, xs[i], ys[j], xs[i + 1], ys[j + 1])
    }
}

@Composable
fun Modifier.neu(kind: String): Modifier {
    val ts = LocalTiles.current ?: return this
    return this.drawBehind { drawTile(ts, kind, 0f, 0f, size.width, size.height) }
}

// ------------------------------------------------------------------ text + icons
@Composable
fun T(text: String, modifier: Modifier = Modifier, size: Int = 13, bold: Boolean = false, color: Color = FB.TX, align: TextAlign? = null,
      spacing: Float = 0f, maxLines: Int = Int.MAX_VALUE) =
    Text(text, modifier, color = color, fontSize = size.sp, fontFamily = Mono, fontWeight = if (bold) FontWeight.Bold else FontWeight.Normal,
        letterSpacing = spacing.sp, textAlign = align, maxLines = maxLines, overflow = TextOverflow.Ellipsis, lineHeight = (size * 1.5f).sp)

@Composable
fun Sub(text: String, modifier: Modifier = Modifier, color: Color = FB.MU) = T(text, modifier, 12, false, color)

@Composable
fun FieldLabel(text: String, modifier: Modifier = Modifier) = T(text.uppercase(), modifier, 11, true, FB.MU, spacing = 0.7f)

@Composable
fun Ico(name: String, size: Dp = 20.dp, modifier: Modifier = Modifier) {
    val ctx = LocalContext.current
    val dir = if (LocalDark.current) "dark" else "light"
    val bmp = remember(name, dir) {
        try { ctx.assets.open("icons/$dir/$name.png").use { BitmapFactory.decodeStream(it) }?.asImageBitmap() } catch (e: Exception) { null }
    }
    if (bmp != null) Image(bmp, null, modifier.size(size), contentScale = ContentScale.Fit)
}

// ------------------------------------------------------------------ panels
@Composable
fun H2(text: String, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(4.dp, 14.dp).clip(RoundedCornerShape(2.dp)).background(FB.AC))
        T(text.uppercase(), Modifier.padding(start = 10.dp), 12, true, FB.MU, spacing = 1.7f)
    }
}

@Composable
fun NeuCard(modifier: Modifier = Modifier, title: String = "", pad: PaddingValues = PaddingValues(18.dp), content: @Composable ColumnScope.() -> Unit) {
    Column(modifier.fillMaxWidth().neu("card").padding(pad), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        if (title.isNotEmpty()) { H2(title); }
        content()
    }
}

@Composable
fun Inset(modifier: Modifier = Modifier, pad: Dp = 8.dp, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier.fillMaxWidth().neu("inset").padding(pad), content = content)
}

@Composable
fun Sep(modifier: Modifier = Modifier) {
    val sd = FB.SD; val sl = FB.SL
    Canvas(modifier.size(4.dp, 28.dp)) {
        drawRect(sd, Offset.Zero, Size(2.dp.toPx(), size.height))
        drawRect(sl, Offset(2.dp.toPx(), 0f), Size(2.dp.toPx(), size.height))
    }
}

// ------------------------------------------------------------------ buttons
@Composable
fun NeuButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, icon: String? = null, main: Boolean = false, on: Boolean = false, tall: Boolean = false) {
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    val sfx = if (tall) "40" else "36"
    val kind = if (main) "pill$sfx" else if (pressed || on) "pillin$sfx" else "pill$sfx"
    val ac = FB.AC
    Row(
        modifier.height(if (tall) 40.dp else 36.dp).neu(kind).let { if (main) it.background(ac, RoundedCornerShape(50)) else it }
            .clip(RoundedCornerShape(50)).clickable(src, null) { onClick() }.padding(horizontal = 18.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center
    ) {
        if (icon != null) { Ico(icon, if (tall) 20.dp else 18.dp); Box(Modifier.width(8.dp)) }
        T(text, size = 13, bold = true, color = if (main) FB.ON else if (on) FB.AC else FB.TX, maxLines = 1)
    }
}

@Composable
fun Seg(options: List<Pair<String, String>>, current: String, onPick: (String) -> Unit, modifier: Modifier = Modifier) {
    Row(modifier.height(42.dp).neu("seg42").padding(4.dp), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
        options.forEach { (k, name) ->
            val sel = k == current
            val ac = FB.AC
            Box(
                Modifier.height(34.dp).let { if (sel) it.neu("segon34").background(ac, RoundedCornerShape(50)) else it }
                    .clip(RoundedCornerShape(50)).clickable { onPick(k) }.padding(horizontal = 14.dp),
                contentAlignment = Alignment.Center
            ) { T(name, size = 12, bold = true, color = if (sel) FB.ON else FB.TX, maxLines = 1) }
        }
    }
}

// ------------------------------------------------------------------ inputs
@Composable
fun NeuField(value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier, placeholder: String = "", password: Boolean = false,
             keyboard: KeyboardOptions = KeyboardOptions.Default, onDone: (() -> Unit)? = null) {
    val ac = FB.AC; val tx = FB.TX
    Box(modifier.fillMaxWidth().height(40.dp).neu("field40").padding(horizontal = 14.dp), contentAlignment = Alignment.CenterStart) {
        BasicTextField(
            value, onChange, singleLine = true, textStyle = TextStyle(color = tx, fontSize = 13.sp, fontFamily = Mono),
            cursorBrush = SolidColor(ac), visualTransformation = if (password) PasswordVisualTransformation() else VisualTransformation.None,
            keyboardOptions = keyboard.copy(imeAction = if (onDone != null) ImeAction.Send else ImeAction.Done),
            keyboardActions = KeyboardActions(onSend = { onDone?.invoke() }, onDone = { onDone?.invoke() }),
            modifier = Modifier.fillMaxWidth()
        )
        if (value.isEmpty() && placeholder.isNotEmpty()) T(placeholder, size = 13, color = FB.MU, maxLines = 1)
    }
}

@Composable
fun NeuSelect(options: List<Pair<String, String>>, current: String, onPick: (String) -> Unit, modifier: Modifier = Modifier) {
    var open by remember { mutableStateOf(false) }
    val mu = FB.MU
    Box(modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().height(40.dp).neu("pillin40").clip(RoundedCornerShape(50)).clickable { open = true }.padding(start = 16.dp, end = 14.dp),
            verticalAlignment = Alignment.CenterVertically) {
            T(options.firstOrNull { it.first == current }?.second ?: "", Modifier.weight(1f), 13, maxLines = 1)
            Canvas(Modifier.size(12.dp, 8.dp)) {
                val p = Path(); p.moveTo(1f, 1f); p.lineTo(size.width / 2, size.height - 1f); p.lineTo(size.width - 1f, 1f)
                drawPath(p, mu, style = Stroke(2.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round))
            }
        }
        DropdownMenu(open, { open = false }, modifier = Modifier.background(FB.BG)) {
            options.forEach { (k, name) -> DropdownMenuItem(text = { T(name, size = 13, color = if (k == current) FB.AC else FB.TX) }, onClick = { open = false; onPick(k) }) }
        }
    }
}

@Composable
fun NeuSwitch(checked: Boolean, onChange: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    val pos by animateFloatAsState(if (checked) 1f else 0f, spring(dampingRatio = 0.6f, stiffness = 500f), label = "sw")
    val ts = LocalTiles.current; val ac = FB.AC
    Box(
        modifier.size(54.dp, 28.dp).clip(CircleShape).clickable { onChange(!checked) }.drawBehind {
            if (ts != null) {
                drawTile(ts, "swtrack", 0f, 0f, size.width, size.height)
                if (pos > 0.01f) drawRoundRect(ac.copy(alpha = pos.coerceIn(0f, 1f)), Offset.Zero, size, androidx.compose.ui.geometry.CornerRadius(14.dp.toPx()))
                drawTile(ts, "thumb", (4 + 24 * pos).dp.toPx(), 3.dp.toPx(), 22.dp.toPx(), 22.dp.toPx())
            }
        }
    )
}

@Composable
fun NeuSlider(value: Float, onChange: (Float) -> Unit, modifier: Modifier = Modifier) {
    val ts = LocalTiles.current; val ac = FB.AC
    Box(
        modifier.fillMaxWidth().height(22.dp)
            .pointerInput(Unit) { detectTapGestures { o -> onChange(((o.x - 11.dp.toPx()) / (size.width - 22.dp.toPx())).coerceIn(0f, 1f)) } }
            .pointerInput(Unit) { detectDragGestures { c, _ -> c.consume(); onChange(((c.position.x - 11.dp.toPx()) / (size.width - 22.dp.toPx())).coerceIn(0f, 1f)) } }
            .drawBehind {
                if (ts != null) {
                    drawTile(ts, "slider12", 0f, 5.dp.toPx(), size.width, 12.dp.toPx())
                    val tx = value * (size.width - 22.dp.toPx())
                    drawRoundRect(ac, Offset(0f, 5.dp.toPx()), Size(maxOf(12.dp.toPx(), tx + 11.dp.toPx()), 12.dp.toPx()), androidx.compose.ui.geometry.CornerRadius(6.dp.toPx()))
                    drawTile(ts, "thumb", tx, 0f, 22.dp.toPx(), 22.dp.toPx())
                }
            }
    )
}

@Composable
fun ConnChip(text: String, dot: Color, modifier: Modifier = Modifier) {
    Row(modifier.height(30.dp).neu("conn30").padding(horizontal = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(12.dp).clip(CircleShape).background(dot))
        T(text, Modifier.padding(start = 8.dp), 12, true, FB.MU, maxLines = 1)
    }
}

@Composable
fun Pill(text: String, color: Color, modifier: Modifier = Modifier) {
    Box(modifier.height(26.dp).neu("conn30").padding(horizontal = 12.dp), contentAlignment = Alignment.Center) { T(text, size = 12, bold = true, color = color, maxLines = 1) }
}

@Composable
fun Orb(color: Color, modifier: Modifier = Modifier) {
    val ts = LocalTiles.current
    Box(modifier.size(92.dp).drawBehind {
        if (ts != null) { drawTile(ts, "orb", 0f, 0f, size.width, size.height); drawTile(ts, "orbdot", 22.dp.toPx(), 22.dp.toPx(), 48.dp.toPx(), 48.dp.toPx()) }
        drawCircle(color, 24.dp.toPx(), center)
    })
}

@Composable
fun Swatch(color: Color, selected: Boolean, onClick: () -> Unit) {
    val ts = LocalTiles.current
    Box(Modifier.size(34.dp).clip(CircleShape).clickable { onClick() }.drawBehind {
        if (ts != null) drawTile(ts, if (selected) "swatchon" else "swatch", 0f, 0f, size.width, size.height)
        drawCircle(color, 8.dp.toPx(), center)
    })
}

/** Calibration dial: 28 ticks, 270 degree arc, raised knob with an accent dot. Drag to turn. */
@Composable
fun Knob(value: Double, lo: Double, hi: Double, step: Double, onChange: (Double) -> Unit, modifier: Modifier = Modifier) {
    val ts = LocalTiles.current; val ac = FB.AC; val mu = FB.MU; val sd = FB.SD
    val f = ((value - lo) / (hi - lo)).coerceIn(0.0, 1.0).toFloat()
    fun set(p: Offset, s: Float) {
        val k = s / 130f
        var a = Math.toDegrees(atan2((p.x / k - 65f).toDouble(), -(p.y / k - 65f).toDouble()))
        if (Math.abs(a) > 135) a = if (a < 0) -135.0 else 135.0
        val v = lo + (a + 135) / 270 * (hi - lo)
        onChange(Math.round(Math.round(v.coerceIn(lo, hi) / step) * step * 100) / 100.0)
    }
    Box(
        modifier.size(130.dp)
            .pointerInput(Unit) { detectTapGestures { set(it, size.width.toFloat()) } }
            .pointerInput(Unit) { detectDragGestures { c, _ -> c.consume(); set(c.position, size.width.toFloat()) } }
            .drawBehind {
                val u = size.width / 130f
                if (ts != null) {
                    drawTile(ts, "dial", 0f, 0f, size.width, size.height)
                    drawTile(ts, "dialin", 26 * u, 26 * u, 78 * u, 78 * u)
                    drawTile(ts, "knob", 34 * u, 34 * u, 62 * u, 62 * u)
                }
                fun pt(r: Float, a: Float) = Offset((65 + r * sin(Math.toRadians(a.toDouble()))).toFloat() * u, (65 - r * cos(Math.toRadians(a.toDouble()))).toFloat() * u)
                for (i in 0 until 28) {
                    val g = -135f + 270f * i / 27f
                    drawLine(if (i / 27f <= f + 1e-4f) ac else mu, pt(55f, g), pt(61f, g), 2.5f * u, StrokeCap.Round)
                }
                val arc = Size(94 * u, 94 * u); val tl = Offset(18 * u, 18 * u)
                drawArc(sd, 135f, 270f, false, tl, arc, style = Stroke(5 * u, cap = StrokeCap.Round))
                if (f > 0) drawArc(ac, 135f, 270f * f, false, tl, arc, style = Stroke(5 * u, cap = StrokeCap.Round))
                drawCircle(ac, 4 * u, pt(20f, -135f + 270f * f))
            }
    )
}
