package com.techminds.flowbeacon

import android.app.Application

/**
 * The app state lives here, not in the activity's ViewModel store, so the connection to the board and the alerts
 * keep working while the screen is closed or the activity is gone (the foreground service keeps the process alive).
 */
class FlowApp : Application() {
    val vm: AppVm by lazy { AppVm(this) }
}
