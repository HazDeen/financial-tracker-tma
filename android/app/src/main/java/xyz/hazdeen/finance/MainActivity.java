package xyz.hazdeen.finance;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.*;
import java.io.*;
import java.util.Collections;

/** Bundled UI and remote API share one HTTPS origin, preserving HttpOnly session cookies. */
public class MainActivity extends Activity {
    private static final String HOST = "finance.hazdeen.xyz";
    private static final String PREFIX = "/__android__/";
    private static final String START = "https://" + HOST + PREFIX + "index.html";
    private WebView web;
    private android.webkit.ValueCallback<Uri[]> fileResult;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        web.setBackgroundColor(Color.rgb(242,242,247));
        android.widget.FrameLayout root = new android.widget.FrameLayout(this);
        root.addView(web, new android.widget.FrameLayout.LayoutParams(-1, -1));
        android.widget.LinearLayout launch = new android.widget.LinearLayout(this);
        launch.setOrientation(android.widget.LinearLayout.VERTICAL);
        launch.setGravity(android.view.Gravity.CENTER);
        launch.setBackgroundColor(Color.rgb(245,248,255));
        android.widget.ImageView mark = new android.widget.ImageView(this);
        mark.setImageResource(R.drawable.ic_finance);
        mark.setContentDescription("Мои финансы");
        int iconSize = (int)(72 * getResources().getDisplayMetrics().density);
        launch.addView(mark, new android.widget.LinearLayout.LayoutParams(iconSize, iconSize));
        android.widget.TextView title = new android.widget.TextView(this);
        title.setText("Мои финансы."); title.setTextSize(25); title.setTextColor(Color.rgb(23,36,58));
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        title.setPadding(0, (int)(26 * getResources().getDisplayMetrics().density), 0, 0);
        launch.addView(title);
        android.widget.TextView subtitle = new android.widget.TextView(this);
        subtitle.setText("Открываем приложение"); subtitle.setTextSize(13); subtitle.setTextColor(Color.rgb(139,154,176));
        subtitle.setPadding(0, 16, 0, 0); launch.addView(subtitle);
        root.addView(launch, new android.widget.FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
        WebView.setWebContentsDebuggingEnabled(false);
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost()) || !uri.getPath().startsWith(PREFIX)) return null;
                String path = uri.getPath().substring(PREFIX.length());
                if (path.isEmpty()) path = "index.html";
                if (path.contains("..") || path.contains("\\")) return missing();
                String mime = path.endsWith(".js") ? "application/javascript" : path.endsWith(".css") ? "text/css" : path.endsWith(".svg") ? "image/svg+xml" : path.endsWith(".html") ? "text/html" : "application/octet-stream";
                try {
                    return new WebResourceResponse(mime, "UTF-8", 200, "OK", Collections.singletonMap("Cache-Control", "no-cache"), getAssets().open("web/" + path));
                } catch (IOException error) { return missing(); }
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if ("https".equals(uri.getScheme()) && HOST.equals(uri.getHost()) && uri.getPath().startsWith(PREFIX)) return false;
                if ("https".equals(uri.getScheme())) {
                    try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (android.content.ActivityNotFoundException ignored) { }
                }
                return true;
            }
            @Override public void onPageCommitVisible(WebView view, String url) { root.removeView(launch); }
            @Override public void onPageFinished(WebView view, String url) { CookieManager.getInstance().flush(); }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, android.webkit.ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileResult != null) fileResult.onReceiveValue(null);
                fileResult = callback;
                Intent choose = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                choose.addCategory(Intent.CATEGORY_OPENABLE);
                choose.setType("*/*");
                choose.putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"application/pdf","text/csv","text/comma-separated-values","application/vnd.ms-excel","text/plain"});
                try { startActivityForResult(choose, 101); }
                catch (android.content.ActivityNotFoundException error) { fileResult.onReceiveValue(null); fileResult = null; }
                return true;
            }
        });
        // Reload bundled UI on process recreation; the persistent cookie retains login.
        android.content.pm.PackageInfo engine = WebView.getCurrentWebViewPackage();
        int engineVersion = 0;
        try { if (engine != null) engineVersion = Integer.parseInt(engine.versionName.split("\\.")[0]); } catch (NumberFormatException ignored) { }
        if (engineVersion < 111) {
            new AlertDialog.Builder(this).setTitle("Обновите компонент Android")
                .setMessage("Для приложения нужен Android System WebView или Chrome версии 111 и новее. Обновите его через Google Play и откройте приложение снова.")
                .setPositiveButton("Обновить", (dialog, which) -> {
                    String appId = engine != null ? engine.packageName : "com.google.android.webview";
                    try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps/details?id=" + appId))); } catch (android.content.ActivityNotFoundException ignored) { }
                    finish();
                }).setNegativeButton("Закрыть", (dialog, which) -> finish()).setCancelable(false).show();
        } else web.loadUrl(START);
    }
    private WebResourceResponse missing() {
        return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == 101 && fileResult != null) {
            fileResult.onReceiveValue(result == RESULT_OK && data != null && data.getData() != null ? new Uri[]{data.getData()} : null);
            fileResult = null;
        }
    }
    @Override public void onBackPressed() {
        // A DOM event lets React close the top sheet or return to the main tab first.
        web.evaluateJavascript("window.dispatchEvent(new Event('android-back', {cancelable:true}))", result -> { if ("true".equals(result)) moveTaskToBack(true); });
    }
    @Override protected void onPause() { CookieManager.getInstance().flush(); web.onPause(); super.onPause(); }
    @Override protected void onResume() { super.onResume(); if (web != null) web.onResume(); }
    @Override protected void onDestroy() { if (fileResult != null) fileResult.onReceiveValue(null); web.destroy(); super.onDestroy(); }
}
