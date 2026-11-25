package com.techminds.flowbeacon

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts

class MainActivity : ComponentActivity() {
    private val vm: AppVm get() = (application as FlowApp).vm
    private val askNotifications = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onStart() { super.onStart(); vm.appVisible = true }
    override fun onStop() { vm.appVisible = false; super.onStop() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        volumeControlStream = android.media.AudioManager.STREAM_MUSIC   // the volume keys control the sound the app plays
        if (android.os.Build.VERSION.SDK_INT >= 33 && !Notifier.canPost(this)) askNotifications.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        setContent { AppRoot(vm) }
    }
}
