package com.techminds.flowbeacon

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.sqrt

/** A trained naive Bayes model (Learn from recordings). */
class NbModel(val labels: List<String>, val prior: List<Double>, val mean: List<List<Double>>, val std: List<List<Double>>, val base: Base) {
    fun toJson(): String {
        fun m(a: List<List<Double>>) = JSONArray(a.map { JSONArray(it) })
        return JSONObject().put("labels", JSONArray(labels)).put("prior", JSONArray(prior)).put("mean", m(mean)).put("std", m(std))
            .put("base", JSONObject().put("flow", base.flow).put("dist", base.dist).put("turb", base.turb).put("sf", base.sf).put("sd", base.sd).put("st", base.st)).toString()
    }

    companion object {
        fun fromJson(s: String): NbModel? = try {
            val o = JSONObject(s)
            fun l(a: JSONArray) = (0 until a.length()).map { a.getDouble(it) }
            fun m(a: JSONArray) = (0 until a.length()).map { l(a.getJSONArray(it)) }
            val b = o.getJSONObject("base")
            NbModel((0 until o.getJSONArray("labels").length()).map { o.getJSONArray("labels").getString(it) }, l(o.getJSONArray("prior")),
                m(o.getJSONArray("mean")), m(o.getJSONArray("std")),
                Base(b.getDouble("flow"), b.getDouble("dist"), b.getDouble("turb"), b.getDouble("sf"), b.getDouble("sd"), b.getDouble("st")))
        } catch (e: Exception) { null }
    }
}

class Labelled(val label: String, val x: DoubleArray)
class CsvRow(val label: String, val r: Reading)

object Ml {
    private val FLOORS = doubleArrayOf(0.05, 0.3, 0.05, 0.15)

    fun features(r: Reading, b: Base): DoubleArray = doubleArrayOf(
        if (b.flow > 0) 1 - r.flow / b.flow else 0.0,
        b.dist - r.dist,
        if (b.turb > 0) (r.turb - b.turb) / b.turb else 0.0,
        if (r.rain) 1.0 else 0.0
    )

    fun train(rows: List<Labelled>, base: Base): NbModel {
        val labels = rows.map { it.label }.distinct()
        val prior = ArrayList<Double>(); val mean = ArrayList<List<Double>>(); val std = ArrayList<List<Double>>()
        for (lab in labels) {
            val xs = rows.filter { it.label == lab }.map { it.x }
            prior.add(xs.size.toDouble() / rows.size)
            val m = ArrayList<Double>(); val s = ArrayList<Double>()
            for (j in 0 until 4) {
                val mu = xs.sumOf { it[j] } / xs.size
                val v = xs.sumOf { (it[j] - mu) * (it[j] - mu) } / xs.size
                m.add(mu); s.add(max(sqrt(v), FLOORS[j]))
            }
            mean.add(m); std.add(s)
        }
        return NbModel(labels, prior, mean, std, base)
    }

    /** Returns the best label and its probability. */
    fun predict(m: NbModel, x: DoubleArray): Pair<String, Double> {
        val lp = m.labels.indices.map { i ->
            var s = ln(m.prior[i])
            for (j in x.indices) {
                val sd = m.std[i][j]
                val z = (x[j] - m.mean[i][j]) / sd
                s += -0.5 * z * z - ln(sd)
            }
            s
        }
        val mx = lp.max()
        val ex = lp.map { exp(it - mx) }
        val tot = ex.sum()
        val k = ex.indices.maxByOrNull { ex[it] } ?: 0
        return m.labels[k] to ex[k] / tot
    }

    fun accuracy(m: NbModel, rows: List<Labelled>): Double =
        if (rows.isEmpty()) 0.0 else rows.count { predict(m, it.x).first == it.label }.toDouble() / rows.size

    private fun num(v: Double): String {
        val t = String.format(java.util.Locale.US, "%.5f", v).trimEnd('0').trimEnd('.')
        return if (t.isEmpty() || t == "-0") "0" else t
    }

    fun header(m: NbModel): String {
        fun f(a: List<Double>) = a.joinToString(",") { num(it) }
        val b = m.base
        return listOf(
            "#define HAS_MODEL 1",
            "const int ML_N=${m.labels.size};",
            "const char* ML_LABELS[]={" + m.labels.joinToString(",") { "\"" + it.filter { c -> c.isLetterOrDigit() || c == ' ' || c == '_' || c == '-' } + "\"" } + "};",
            "const float ML_PRIOR[]={" + f(m.prior) + "};",
            "const float ML_MEAN[][4]={" + m.mean.joinToString(",") { "{" + f(it) + "}" } + "};",
            "const float ML_STD[][4]={" + m.std.joinToString(",") { "{" + f(it) + "}" } + "};",
            String.format(java.util.Locale.US, "const float BASE_FLOW=%.3f,BASE_DIST=%.3f,BASE_TURB=%.1f;", b.flow, b.dist, b.turb),
            ""
        ).joinToString("\n")
    }

    fun parseCsv(text: String, defLabel: String): List<CsvRow> {
        val lines = text.replace("\r", "").split("\n").filter { it.isNotEmpty() }
        if (lines.size < 2) return emptyList()
        val h = lines[0].split(",").map { it.trim().lowercase().replace("\"", "") }
        val fi = h.indexOf("flow"); val di = h.indexOf("dist"); val ti = h.indexOf("turb")
        if (fi < 0 || di < 0 || ti < 0) return emptyList()
        val li = h.indexOf("label"); val ri = h.indexOf("rain")
        val out = ArrayList<CsvRow>()
        for (line in lines.drop(1)) {
            val c = line.split(",").map { it.replace("\"", "") }
            try {
                val lab = if (li >= 0 && li < c.size) c[li] else ""
                val rain = ri >= 0 && ri < c.size && (c[ri].toDoubleOrNull() ?: 0.0) != 0.0
                out.add(CsvRow(lab.ifEmpty { defLabel }, Reading(c[fi].toDouble(), c[di].toDouble(), c[ti].toDouble(), rain)))
            } catch (e: Exception) { }
        }
        return out
    }
}
