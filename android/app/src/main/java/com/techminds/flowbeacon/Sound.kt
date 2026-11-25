package com.techminds.flowbeacon

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import android.media.SoundPool
import android.os.Build
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator

/**
 * Plays the app sounds.
 *
 * Why the old version was silent: every MediaPlayer was a local variable that nothing held on to, so the garbage
 * collector could release it before or while it played, and the click and dial sounds were never connected at all.
 * Now alert sounds use a MediaPlayer that is kept in [live] until it finishes, and the very short UI sounds
 * (click, dial tick, dial spin) use a SoundPool loaded once at start-up. Everything plays on the media stream.
 */
class Sound(private val ctx: Context, private val prefs: Prefs) {
    private val ids = mapOf(
        "baseline" to R.raw.baseline, "click" to R.raw.click, "connect" to R.raw.connect, "disconnect" to R.raw.disconnect,
        "normal" to R.raw.normal, "overflow" to R.raw.overflow, "possible" to R.raw.possible, "predict" to R.raw.predict,
        "rain" to R.raw.rain, "risk" to R.raw.risk, "warning" to R.raw.warning,
        "knob_tick" to R.raw.knob_tick, "knob_spin" to R.raw.knob_spin
    )
    private val shortNames = listOf("click", "knob_tick", "knob_spin")
    private val last = HashMap<String, Long>()
    private val live = ArrayList<MediaPlayer>()          // strong references: a player must not be garbage collected while it plays
    private val attrs = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA)
        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
        .build()

    private var pool: SoundPool? = null
    private val poolIds = HashMap<String, Int>()
    private val poolReady = HashSet<Int>()
    private var spinStream = 0

    /** Set by the view model: true while quiet hours are active. Everything is silent then, except overflow. */
    var quiet: () -> Boolean = { false }

    init {
        try {
            val p = SoundPool.Builder().setMaxStreams(8).setAudioAttributes(attrs).build()
            p.setOnLoadCompleteListener { _, sid, status -> if (status == 0) synchronized(poolReady) { poolReady.add(sid) } }
            shortNames.forEach { n -> ids[n]?.let { poolIds[n] = p.load(ctx, it, 1) } }
            pool = p
        } catch (e: Exception) {
            pool = null
        }
    }

    private fun gate(name: String): Boolean {
        if (prefs.mute) return false
        val key = if (name == "click" || name.startsWith("knob")) "ui" else name
        if (!prefs.sndOn(key)) return false
        if (name != "overflow" && quiet()) return false
        return true
    }

    private fun vol(scale: Float = 1f) = (prefs.vol * scale).coerceIn(0f, 1f)

    fun play(name: String, minGapMs: Long = 0) {
        if (!gate(name)) return
        val id = ids[name] ?: return
        val now = SystemClock.elapsedRealtime()
        if (now - (last[name] ?: -100000L) < minGapMs) return
        last[name] = now
        if (name in shortNames) playShort(name, 1f, 1f) else playLong(id)
    }

    private fun playShort(name: String, rate: Float, scale: Float): Int {
        val p = pool ?: return 0
        val sid = poolIds[name] ?: return 0
        val ready = synchronized(poolReady) { sid in poolReady }
        if (!ready) { ids[name]?.let { playLong(it) }; return 0 }
        val v = vol(scale)
        return p.play(sid, v, v, 1, 0, rate.coerceIn(0.5f, 2f))
    }

    private fun playLong(id: Int) {
        try {
            val mp = MediaPlayer()
            val afd = ctx.resources.openRawResourceFd(id) ?: return
            try {
                mp.setAudioAttributes(attrs)
                mp.setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
            } finally {
                try { afd.close() } catch (e: Exception) { }
            }
            val v = vol()
            mp.setVolume(v, v)
            mp.setOnPreparedListener { it.start() }
            mp.setOnCompletionListener { drop(it) }
            mp.setOnErrorListener { p, _, _ -> drop(p); true }
            synchronized(live) {
                live.add(mp)
                while (live.size > 6) drop(live[0])
            }
            mp.prepareAsync()
        } catch (e: Exception) {
            // no sound is better than a crash
        }
    }

    private fun drop(p: MediaPlayer) {
        synchronized(live) { live.remove(p) }
        try { p.release() } catch (e: Exception) { }
    }

    private var tickAt = 0L

    /** One notch of a calibration dial; [f] is the dial position 0..1 and shifts the pitch a little, like the web app. */
    fun knobTick(f: Float) {
        if (!gate("knob_tick")) return
        val t = SystemClock.elapsedRealtime()
        if (t - tickAt < 38) return
        tickAt = t
        playShort("knob_tick", 0.92f + f * 0.2f, 0.8f)
    }

    fun knobSpin() {
        if (!gate("knob_spin")) return
        knobStop()
        spinStream = playShort("knob_spin", 1f, 0.8f)
    }

    fun knobStop() {
        if (spinStream != 0) { try { pool?.stop(spinStream) } catch (e: Exception) { }; spinStream = 0 }
    }

    fun release() {
        knobStop()
        synchronized(live) { live.toList() }.forEach { drop(it) }
        try { pool?.release() } catch (e: Exception) { }
        pool = null
    }

    @Suppress("DEPRECATION")
    fun buzz(ms: Long = 400) {
        if (!prefs.vibrate) return
        try {
            val v = ctx.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator ?: return
            if (Build.VERSION.SDK_INT >= 26) v.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE)) else v.vibrate(ms)
        } catch (e: Exception) {
        }
    }
}
