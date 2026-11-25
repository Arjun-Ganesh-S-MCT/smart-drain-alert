package com.techminds.flowbeacon

import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class UpdateInfo(val current: String, val latest: String, val newer: Boolean, val url: String, val error: String = "")

/** Update check: asks GitHub for the latest release. Run it on a background thread. */
object Updater {
    const val VERSION = "2.0.1"
    private const val REPO = "Arjun-Ganesh-S-MCT/smart-drain-alert"

    fun cmp(a: String, b: String): Int {
        val x = a.split(".").map { it.toIntOrNull() ?: 0 }; val y = b.split(".").map { it.toIntOrNull() ?: 0 }
        for (i in 0 until 3) { val d = (x.getOrElse(i) { 0 }) - (y.getOrElse(i) { 0 }); if (d != 0) return d }
        return 0
    }

    fun check(): UpdateInfo {
        return try {
            val c = OkHttpClient.Builder().callTimeout(10, TimeUnit.SECONDS).build()
            val req = Request.Builder().url("https://api.github.com/repos/$REPO/releases/latest")
                .header("Accept", "application/vnd.github+json").header("User-Agent", "FlowBeacon").build()
            c.newCall(req).execute().use { r ->
                if (!r.isSuccessful) return UpdateInfo(VERSION, "", false, "", "HTTP ${r.code}")
                val j = JSONObject(r.body?.string() ?: "{}")
                val latest = j.optString("tag_name", "").removePrefix("v")
                var url = j.optString("html_url", "")
                if (!url.startsWith("https://github.com/")) url = "https://github.com/$REPO/releases/latest"
                UpdateInfo(VERSION, latest, latest.isNotEmpty() && cmp(latest, VERSION) > 0, url)
            }
        } catch (e: Exception) {
            UpdateInfo(VERSION, "", false, "", (e.message ?: "offline").take(120))
        }
    }
}
