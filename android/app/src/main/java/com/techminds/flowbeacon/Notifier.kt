package com.techminds.flowbeacon

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

/** Notification channels and the alert notifications (background alerts). */
object Notifier {
    const val CH_MONITOR = "monitor"
    const val CH_ALERT = "alerts"
    const val ID_MONITOR = 1
    private var alertId = 100

    fun channels(ctx: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(NotificationChannel(CH_MONITOR, "Monitoring", NotificationManager.IMPORTANCE_LOW).apply { description = "Shown while FlowBeacon watches the board in the background" })
        nm.createNotificationChannel(NotificationChannel(CH_ALERT, "Drain alerts", NotificationManager.IMPORTANCE_HIGH).apply { description = "Blockage and overflow warnings"; enableVibration(true) })
    }

    private fun open(ctx: Context): PendingIntent {
        val i = Intent(ctx, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
        return PendingIntent.getActivity(ctx, 0, i, PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0))
    }

    fun monitor(ctx: Context, text: String): Notification {
        channels(ctx)
        return NotificationCompat.Builder(ctx, CH_MONITOR).setSmallIcon(R.mipmap.ic_launcher).setContentTitle("FlowBeacon").setContentText(text)
            .setOngoing(true).setContentIntent(open(ctx)).setPriority(NotificationCompat.PRIORITY_LOW).build()
    }

    fun canPost(ctx: Context) = Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    fun alert(ctx: Context, title: String, text: String) {
        if (!canPost(ctx)) return
        try {
            channels(ctx)
            val n = NotificationCompat.Builder(ctx, CH_ALERT).setSmallIcon(R.mipmap.ic_launcher).setContentTitle(title).setContentText(text)
                .setStyle(NotificationCompat.BigTextStyle().bigText(text)).setAutoCancel(true).setContentIntent(open(ctx))
                .setPriority(NotificationCompat.PRIORITY_HIGH).setDefaults(NotificationCompat.DEFAULT_ALL).build()
            (ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(alertId++, n)
        } catch (e: Exception) { }
    }

    fun updateMonitor(ctx: Context, text: String) {
        if (!canPost(ctx)) return
        try { (ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager).notify(ID_MONITOR, monitor(ctx, text)) } catch (e: Exception) { }
    }
}

/** Foreground service: its only job is to keep the process (and so the connection to the board) alive in the background. */
class AlertService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val n = Notifier.monitor(this, intent?.getStringExtra("text") ?: "Watching the drain")
        try {
            if (Build.VERSION.SDK_INT >= 29) startForeground(Notifier.ID_MONITOR, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
            else startForeground(Notifier.ID_MONITOR, n)
        } catch (e: Exception) {
            stopSelf()
        }
        return START_STICKY
    }

    companion object {
        fun start(ctx: Context, text: String) {
            try { ContextCompat.startForegroundService(ctx, Intent(ctx, AlertService::class.java).putExtra("text", text)) } catch (e: Exception) { }
        }
        fun stop(ctx: Context) { try { ctx.stopService(Intent(ctx, AlertService::class.java)) } catch (e: Exception) { } }
    }
}
