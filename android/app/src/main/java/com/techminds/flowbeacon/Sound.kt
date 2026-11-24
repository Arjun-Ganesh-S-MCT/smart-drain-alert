package com.techminds.flowbeacon

import android.content.Context
import android.media.MediaPlayer
import android.os.SystemClock
import android.os.Vibrator

/** Plays the short alert sounds. One small MediaPlayer per play, released when it ends (works on every Android version). */
class Sound(private val ctx: Context, private val prefs: Prefs) {
    private val ids = mapOf(
        "baseline" to R.raw.baseline, "click" to R.raw.click, "connect" to R.raw.connect, "disconnect" to R.raw.disconnect,
        "normal" to R.raw.normal, "overflow" to R.raw.overflow, "possible" to R.raw.possible, "predict" to R.raw.predict,
        "rain" to R.raw.rain, "risk" to R.raw.risk, "warning" to R.raw.warning
    )
    private val last = HashMap<String, Long>()

    fun play(name: String, minGapMs: Long = 0) {
        if (prefs.mute || !prefs.sndOn(name)) return
        val id = ids[name] ?: return
        val now = SystemClock.elapsedRealtime()
        if (now - (last[name] ?: -100000L) < minGapMs) return
        last[name] = now
        try {
            val mp = MediaPlayer.create(ctx, id) ?: return
            mp.setVolume(prefs.vol, prefs.vol)
            mp.setOnCompletionListener { it.release() }
            mp.setOnErrorListener { p, _, _ -> p.release(); true }
            mp.start()
        } catch (e: Exception) {
            // no sound is better than a crash
        }
    }

    @Suppress("DEPRECATION")
    fun buzz(ms: Long = 400) {
        if (!prefs.vibrate) return
        try {
            (ctx.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator)?.vibrate(ms)
        } catch (e: Exception) {
        }
    }
}
