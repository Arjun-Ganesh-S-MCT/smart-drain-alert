package com.techminds.flowbeacon

import android.content.Context
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.core.view.WindowCompat

val LocalPal = staticCompositionLocalOf { Palettes.ALL.getValue("coral_light") }
val LocalMono = staticCompositionLocalOf<FontFamily> { FontFamily.Monospace }
val LocalDark = staticCompositionLocalOf { false }

/** Live theme colours (7 accents x light / dark), read inside composables like constants. */
object FB {
    val BG: Color @Composable get() = Color(LocalPal.current.bg)
    val SD: Color @Composable get() = Color(LocalPal.current.sd)
    val SL: Color @Composable get() = Color(LocalPal.current.sl)
    val TX: Color @Composable get() = Color(LocalPal.current.tx)
    val MU: Color @Composable get() = Color(LocalPal.current.mu)
    val AC: Color @Composable get() = Color(LocalPal.current.ac)
    val ON: Color @Composable get() = Color(LocalPal.current.on)
}

val Mono: FontFamily @Composable get() = LocalMono.current

private fun loadMono(ctx: Context): FontFamily = try {
    val a = ctx.assets
    FontFamily(
        Font("fonts/JetBrainsMono-Regular.ttf", a, FontWeight.Normal),
        Font("fonts/JetBrainsMono-Bold.ttf", a, FontWeight.SemiBold),
        Font("fonts/JetBrainsMono-Bold.ttf", a, FontWeight.Bold)
    )
} catch (e: Exception) { FontFamily.Monospace }

@Composable
fun FlowTheme(accent: String, mode: String, content: @Composable () -> Unit) {
    val ctx = LocalContext.current
    val dark = when (mode) { "dark" -> true; "light" -> false; else -> isSystemInDarkTheme() }
    val key = accent + "_" + (if (dark) "dark" else "light")
    val pal = Palettes.ALL[key] ?: Palettes.ALL.getValue("coral_light")
    val fam = remember { loadMono(ctx) }
    val tiles = remember(key) { TileSet(ctx, key) }
    val view = LocalView.current
    SideEffect {
        val w = (view.context as? android.app.Activity)?.window
        if (w != null) {
            @Suppress("DEPRECATION") run { w.statusBarColor = Color(pal.bg).toArgb(); w.navigationBarColor = Color(pal.bg).toArgb() }
            WindowCompat.getInsetsController(w, view)?.isAppearanceLightStatusBars = !dark
        }
    }
    CompositionLocalProvider(LocalPal provides pal, LocalMono provides fam, LocalDark provides dark, LocalTiles provides tiles) {
        MaterialTheme(
            colorScheme = (if (dark) darkColorScheme() else lightColorScheme()).copy(
                primary = Color(pal.ac), onPrimary = Color(pal.on), background = Color(pal.bg), surface = Color(pal.bg),
                onSurface = Color(pal.tx), onBackground = Color(pal.tx)
            ),
            content = content
        )
    }
}
