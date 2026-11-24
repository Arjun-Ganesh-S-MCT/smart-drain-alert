package com.techminds.flowbeacon

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text

private const val TOTAL = 9.0f   // seconds: a slow intro; tap to skip

private fun seg(t: Float, start: Float, dur: Float) = ((t - start) / dur).coerceIn(0f, 1f)

/** Same sequence as the desktop splash (TechMinds, then Drip and FlowBeacon, with a progress bar), played slowly. */
@Composable
fun IntroScreen(onDone: () -> Unit) {
    val t = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        t.animateTo(TOTAL, tween((TOTAL * 1000).toInt(), easing = LinearEasing))
        onDone()
    }
    Box(
        Modifier.fillMaxSize().background(FB.BG)
            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) { onDone() }
    ) {
        // scene A: TechMinds presents
        Column(
            Modifier.fillMaxSize().padding(bottom = 70.dp).graphicsLayer {
                alpha = seg(t.value, 0.3f, 1.3f) * (1f - seg(t.value, 4.4f, 0.9f))
            },
            horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center
        ) {
            Image(
                painterResource(R.drawable.img_techminds), "TechMinds",
                Modifier.height(130.dp).graphicsLayer { val s = 0.88f + 0.12f * seg(t.value, 0.3f, 1.6f); scaleX = s; scaleY = s }
            )
            Text(
                "PRESENTS", color = FB.TX, fontSize = 13.sp, letterSpacing = 7.sp, fontFamily = Mono,
                modifier = Modifier.padding(top = 18.dp).graphicsLayer { alpha = seg(t.value, 2.1f, 1.1f) }
            )
        }
        // scene B: Drip and the app name
        Column(
            Modifier.fillMaxSize().padding(bottom = 70.dp).graphicsLayer { alpha = seg(t.value, 5.4f, 1.2f) },
            horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center
        ) {
            Image(
                painterResource(R.drawable.img_drip_full), "Drip",
                Modifier.height(128.dp).graphicsLayer {
                    val k = seg(t.value, 5.4f, 1.5f)
                    translationY = (1f - k) * 46.dp.toPx()
                }
            )
            Text(
                buildAnnotatedString {
                    withStyle(SpanStyle(color = FB.TX)) { append("Flow") }
                    withStyle(SpanStyle(color = FB.AC)) { append("Beacon") }
                },
                fontSize = 28.sp, fontWeight = FontWeight.Bold, fontFamily = Mono, letterSpacing = 1.sp,
                modifier = Modifier.padding(top = 14.dp)
            )
            Text(
                "drain blockage prediction", color = FB.MU, fontSize = 11.sp, letterSpacing = 1.sp, fontFamily = Mono,
                modifier = Modifier.padding(top = 6.dp).graphicsLayer { alpha = seg(t.value, 6.6f, 1.1f) }
            )
        }
        // progress bar
        Box(
            Modifier.align(Alignment.BottomCenter).padding(start = 44.dp, end = 44.dp, bottom = 36.dp).fillMaxWidth()
                .height(12.dp).neu("slider12")
        ) {
            Box(
                Modifier.fillMaxSize().graphicsLayer {
                    transformOrigin = androidx.compose.ui.graphics.TransformOrigin(0f, 0.5f)
                    scaleX = seg(t.value, 0.2f, 8.2f)
                }.clip(RoundedCornerShape(50)).background(FB.AC)
            )
        }
    }
}
