package com.techminds.flowbeacon

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import java.util.TimeZone

data class HRow(val node: String, val t: Long, val n: Int, val f: Double, val l: Double, val tb: Double, val r: Double, val lvl: Int)
data class HGroup(val t: Long, val n: Int, val f: Double, val l: Double, val lmin: Double, val lmax: Double, val lvl: Int)

/** One averaged row per minute per drain, kept 90 days (the History tab). */
class HistoryDb(ctx: Context) : SQLiteOpenHelper(ctx, "history.db", null, 1) {
    private class Bucket(val node: String, val t: Long) { var n = 0; var f = 0.0; var l = 0.0; var tb = 0.0; var r = 0.0; var lvl = 0 }
    private val open = HashMap<String, Bucket>()

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE mins (node TEXT, t INTEGER, n INTEGER, f REAL, l REAL, tb REAL, r REAL, lvl INTEGER, PRIMARY KEY (node, t))")
    }

    override fun onUpgrade(db: SQLiteDatabase, o: Int, n: Int) { }

    fun add(node: String, d: Reading, lvl: Int, now: Long = System.currentTimeMillis()) {
        val m = now / 60000 * 60000
        var b = open[node]
        if (b == null || b.t != m) { flush(b); b = Bucket(node, m); open[node] = b }
        b.n++; b.f += d.flow; b.l += d.dist; b.tb += d.turb; b.r += if (d.rain) 1 else 0; b.lvl = maxOf(b.lvl, lvl)
    }

    private fun flush(b: Bucket?) {
        if (b == null || b.n == 0) return
        try {
            val v = ContentValues().apply {
                put("node", b.node); put("t", b.t); put("n", b.n); put("f", b.f / b.n); put("l", b.l / b.n)
                put("tb", b.tb / b.n); put("r", b.r / b.n); put("lvl", b.lvl)
            }
            writableDatabase.insertWithOnConflict("mins", null, v, SQLiteDatabase.CONFLICT_REPLACE)
        } catch (e: Exception) { }
    }

    fun flushAll(olderThanMs: Long = 0) {
        val now = System.currentTimeMillis()
        open.values.toList().forEach { if (olderThanMs == 0L || it.t < now - olderThanMs) flush(it) }
    }

    fun range(node: String, a: Long, b: Long): List<HRow> {
        flushAll(60000)
        val out = ArrayList<HRow>()
        try {
            readableDatabase.rawQuery("SELECT node,t,n,f,l,tb,r,lvl FROM mins WHERE node=? AND t>=? AND t<=? ORDER BY t", arrayOf(node, a.toString(), b.toString())).use { c ->
                while (c.moveToNext()) out.add(HRow(c.getString(0), c.getLong(1), c.getInt(2), c.getDouble(3), c.getDouble(4), c.getDouble(5), c.getDouble(6), c.getInt(7)))
            }
        } catch (e: Exception) { }
        return out
    }

    fun prune(days: Int = 90) {
        try { writableDatabase.delete("mins", "t<?", arrayOf((System.currentTimeMillis() - days * 86400000L).toString())) } catch (e: Exception) { }
    }
}

object HistCalc {
    /** Hourly groups for a 1 day range, daily groups for longer ranges. */
    fun group(rows: List<HRow>, days: Int): List<HGroup> {
        class G(val t: Long) { var n = 0; var f = 0.0; var l = 0.0; var lmin = 1e9; var lmax = -1e9; var lvl = 0 }
        val grp = java.util.TreeMap<Long, G>()
        val cal = Calendar.getInstance()
        for (r in rows) {
            val k = if (days == 1) r.t / 3600000 * 3600000 else { cal.timeInMillis = r.t; cal.set(Calendar.HOUR_OF_DAY, 0); cal.set(Calendar.MINUTE, 0); cal.set(Calendar.SECOND, 0); cal.set(Calendar.MILLISECOND, 0); cal.timeInMillis }
            val g = grp.getOrPut(k) { G(k) }
            g.n += r.n; g.f += r.f * r.n; g.l += r.l * r.n; g.lmin = minOf(g.lmin, r.l); g.lmax = maxOf(g.lmax, r.l); g.lvl = maxOf(g.lvl, r.lvl)
        }
        return grp.values.map { HGroup(it.t, it.n, it.f / it.n, it.l / it.n, it.lmin, it.lmax, it.lvl) }
    }

    fun csv(rows: List<HRow>): String {
        val f = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply { timeZone = TimeZone.getTimeZone("UTC") }
        return (listOf("node,time,minutes,avg_flow,avg_dist,avg_turb,rain_fraction,worst_level") + rows.map {
            String.format(Locale.US, "%s,%s,%d,%.3f,%.2f,%.0f,%.2f,%d", it.node, f.format(Date(it.t)), it.n, it.f, it.l, it.tb, it.r, it.lvl)
        }).joinToString("\n")
    }
}
