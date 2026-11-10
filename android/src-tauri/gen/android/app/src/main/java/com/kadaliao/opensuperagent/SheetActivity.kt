package com.kadaliao.opensuperagent

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.CookieManager
import android.widget.FrameLayout
import android.content.pm.ShortcutInfo
import android.content.pm.ShortcutManager
import android.graphics.drawable.Icon
import android.os.Build
import java.net.URI

class SheetActivity : Activity() {
  private lateinit var web: WebView
  private var origin: String = ""

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val url = intent.getStringExtra(EXTRA_URL).orEmpty()
    origin = intent.getStringExtra(EXTRA_ORIGIN).orEmpty()
    if (!sameOrigin(url, origin)) {
      finish()
      return
    }
    web = WebView(this)
    web.settings.javaScriptEnabled = true
    web.settings.domStorageEnabled = true
    CookieManager.getInstance().setAcceptCookie(true)
    CookieManager.getInstance().setAcceptThirdPartyCookies(web, true)
    web.webViewClient = object : WebViewClient() {
      override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
        val next = request.url.toString()
        if (request.isForMainFrame && !sameOrigin(next, origin)) {
          startActivity(Intent(Intent.ACTION_VIEW, request.url))
          return true
        }
        return false
      }
    }
    setContentView(web, FrameLayout.LayoutParams(
      FrameLayout.LayoutParams.MATCH_PARENT,
      FrameLayout.LayoutParams.MATCH_PARENT
    ))
    web.loadUrl(url)
  }

  override fun onDestroy() {
    if (this::web.isInitialized) {
      web.stopLoading()
      web.destroy()
    }
    super.onDestroy()
  }

    companion object {
    const val EXTRA_URL = "url"
    const val EXTRA_ORIGIN = "origin"

    fun sameOrigin(url: String, origin: String): Boolean {
      return try {
        val a = URI(url)
        val b = URI(origin)
        a.scheme.equals(b.scheme, true) &&
          a.host.equals(b.host, true) &&
          port(a) == port(b)
      } catch (_: Exception) {
        false
      }
    }

    private fun port(u: URI): Int {
      if (u.port != -1) return u.port
      return if (u.scheme.equals("https", true)) 443 else 80
    }

    fun setCount(activity: Activity, count: Int) {
      if (Build.VERSION.SDK_INT < 25) return
      val manager = activity.getSystemService(ShortcutManager::class.java) ?: return
      val n = count.coerceAtLeast(0)
      if (n == 0) {
        manager.removeDynamicShortcuts(listOf("pending"))
        return
      }
      val label = if (n == 1) "1 pending" else "$n pending"
      val info = ShortcutInfo.Builder(activity, "pending")
        .setShortLabel(label)
        .setLongLabel(label)
        .setIcon(Icon.createWithResource(activity, R.mipmap.ic_launcher))
        .setIntent(Intent(activity, MainActivity::class.java).setAction(Intent.ACTION_MAIN))
        .build()
      manager.dynamicShortcuts = listOf(info)
    }
  }
}
