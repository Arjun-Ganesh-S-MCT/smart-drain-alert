package com.techminds.flowbeacon

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbManager
import android.os.Build
import androidx.core.content.ContextCompat
import com.hoho.android.usbserial.driver.UsbSerialDriver
import com.hoho.android.usbserial.driver.UsbSerialPort
import com.hoho.android.usbserial.driver.UsbSerialProber
import com.hoho.android.usbserial.util.SerialInputOutputManager

/** USB serial link to the ESP32-S3 (USB OTG cable). Lines arrive through [onLine] on a background thread. */
class UsbLink(private val ctx: Context, private val onLine: (String) -> Unit, private val onState: (Boolean, String) -> Unit) {
    private val usb = ctx.getSystemService(Context.USB_SERVICE) as UsbManager
    private var port: UsbSerialPort? = null
    private var io: SerialInputOutputManager? = null
    private val buf = StringBuilder()
    private var receiver: BroadcastReceiver? = null

    val isOpen: Boolean get() = port != null

    fun drivers(): List<UsbSerialDriver> = try { UsbSerialProber.getDefaultProber().findAllDrivers(usb) } catch (e: Exception) { emptyList() }

    fun connect(d: UsbSerialDriver) {
        if (usb.hasPermission(d.device)) { open(d); return }
        val act = ctx.packageName + ".USB_PERMISSION"
        val r = object : BroadcastReceiver() {
            override fun onReceive(c: Context, i: Intent) {
                try { ctx.unregisterReceiver(this) } catch (e: Exception) { }
                receiver = null
                if (usb.hasPermission(d.device)) open(d) else onState(false, "USB permission was refused")
            }
        }
        receiver = r
        ContextCompat.registerReceiver(ctx, r, IntentFilter(act), ContextCompat.RECEIVER_NOT_EXPORTED)
        val flags = if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0
        usb.requestPermission(d.device, PendingIntent.getBroadcast(ctx, 0, Intent(act).setPackage(ctx.packageName), flags))
    }

    private fun open(d: UsbSerialDriver) {
        try {
            val conn = usb.openDevice(d.device)
            if (conn == null) { onState(false, "Could not open the USB device"); return }
            val p = d.ports[0]
            p.open(conn)
            p.setParameters(115200, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
            try { p.setDTR(true); p.setRTS(false) } catch (e: Exception) { }
            port = p; buf.setLength(0)
            val m = SerialInputOutputManager(p, object : SerialInputOutputManager.Listener {
                override fun onNewData(data: ByteArray) { feed(String(data, Charsets.UTF_8)) }
                override fun onRunError(e: Exception) { close(); onState(false, "USB disconnected") }
            })
            io = m
            m.start()
            onState(true, "Connected (USB)")
        } catch (e: Exception) {
            close()
            onState(false, "USB error: " + (e.message ?: "unknown").take(80))
        }
    }

    private fun feed(s: String) {
        buf.append(s)
        while (true) {
            val i = buf.indexOf("\n")
            if (i < 0) break
            val line = buf.substring(0, i).trim()
            buf.delete(0, i + 1)
            if (line.isNotEmpty()) onLine(line)
        }
        if (buf.length > 4000) buf.setLength(0)
    }

    fun write(s: String): Boolean = try { port?.write(s.toByteArray(Charsets.UTF_8), 2000); port != null } catch (e: Exception) { false }

    fun close() {
        try { io?.stop() } catch (e: Exception) { }
        try { port?.close() } catch (e: Exception) { }
        io = null; port = null
        receiver?.let { try { ctx.unregisterReceiver(it) } catch (e: Exception) { } }
        receiver = null
    }
}
