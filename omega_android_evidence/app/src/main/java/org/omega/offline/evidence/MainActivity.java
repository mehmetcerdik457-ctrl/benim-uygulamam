package org.omega.offline.evidence;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.text.InputType;

import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Offline, read-only document hash comparison only. No network or account login.
 * Selecting a document grants temporary URI read access for that one document.
 * Does not prove trusted origin or replace an owner-signature verification.
 */
public final class MainActivity extends Activity {
    private static final int PICK_DOCUMENT = 301;
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private Button choose;
    private EditText expectedInput;
    private TextView resultView;
    private volatile boolean busy;

    private int dp(int value) {
        return (int) (getResources().getDisplayMetrics().density * value + 0.5f);
    }

    private TextView text(String content, int size) {
        TextView view = new TextView(this);
        view.setText(content);
        view.setTextSize(size);
        view.setPadding(0, dp(6), 0, dp(6));
        return view;
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(24), dp(20), dp(24));
        root.setFitsSystemWindows(true);
        if (Build.VERSION.SDK_INT >= 35) {
            root.setOnApplyWindowInsetsListener((view, windowInsets) -> {
                Insets bars = windowInsets.getInsets(WindowInsets.Type.systemBars());
                root.setPadding(dp(20) + bars.left, dp(24) + bars.top,
                        dp(20) + bars.right, dp(24) + bars.bottom);
                return windowInsets;
            });
        }

        TextView title = text("OMEGA • Çevrimdışı Kanıt Denetçisi", 22);
        title.setContentDescription("OMEGA çevrimdışı kanıt denetçisi");
        root.addView(title);

        root.addView(text(
            "Yerel dosyanın SHA-256 özetini hesaplar. İstersen önceden doğrulanmış 64 haneli özeti girip karşılaştır.",
            16));
        root.addView(text(
            "SINIR: Sadece dosya bütünlüğü. Dosyanın güvenilir olduğunu, kaynağın sahibini, OMEGA üretim kabulünü veya APK imzasını kanıtlamaz.",
            14));

        TextView expectedLabel = text("Beklenen SHA-256 (isteğe bağlı)", 16);
        root.addView(expectedLabel);
        expectedInput = new EditText(this);
        expectedInput.setId(View.generateViewId());
        expectedInput.setSingleLine(true);
        expectedInput.setInputType(InputType.TYPE_CLASS_TEXT |
                InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        expectedInput.setHint("64 hex karakter veya boş bırak");
        expectedInput.setContentDescription("Beklenen SHA 256 değeri, 64 onaltılık karakter");
        expectedLabel.setLabelFor(expectedInput.getId());
        root.addView(expectedInput);

        choose = new Button(this);
        choose.setText("Dosya seç ve SHA-256 hesapla");
        choose.setAllCaps(false);
        choose.setContentDescription("Tek bir yerel dosya seç ve çevrimdışı özetini hesapla");
        choose.setOnClickListener(view -> pickDocument());
        root.addView(choose);

        resultView = text("Henüz dosya seçilmedi. Ağ erişimi ve kullanıcı hesabı kullanılmaz.", 15);
        resultView.setTextIsSelectable(true);
        resultView.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        root.addView(resultView);

        root.addView(text(
            "İzin: Android belge seçicisinin yalnızca seçtiğin dosya için verdiği geçici okuma erişimi. En çok 64 MiB, yerel hesaplama; yedekleme ve dosya saklama yok.",
            14));
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(root);
        setContentView(scroll);
    }

    private void pickDocument() {
        if (busy) return;
        String expected = expectedInput.getText().toString().trim();
        if (!expected.isEmpty() && !EvidenceHasher.isValidExpectedHash(expected)) {
            resultView.setText("RET: Beklenen SHA-256 tam 64 hex karakter olmalı.");
            return;
        }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            startActivityForResult(intent, PICK_DOCUMENT);
        } catch (RuntimeException ignored) {
            resultView.setText("Belge seçici açılamadı; hiçbir dosya okunmadı.");
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != PICK_DOCUMENT || resultCode != RESULT_OK || data == null) return;
        Uri uri = data.getData();
        if (uri == null || !"content".equals(uri.getScheme()) || busy) {
            resultView.setText("RET: Güvenilir biçimde seçilmiş bir belge bulunamadı.");
            return;
        }
        final String expected = expectedInput.getText().toString().trim();
        if (!expected.isEmpty() && !EvidenceHasher.isValidExpectedHash(expected)) {
            resultView.setText("RET: Beklenen SHA-256 hatalı. Dosya okunmadı.");
            return;
        }
        busy = true;
        choose.setEnabled(false);
        resultView.setText("Dosya yalnızca cihazda okunuyor, özet hesaplanıyor…");

        io.execute(() -> {
            final String message;
            try (InputStream stream = getContentResolver().openInputStream(uri)) {
                if (stream == null) throw new IOException("No readable stream");
                EvidenceHasher.Result result = EvidenceHasher.calculate(stream);
                String comparison = expected.isEmpty()
                    ? "Beklenen özet girilmedi; eşleşme doğrulanmadı."
                    : EvidenceHasher.matches(expected, result.sha256)
                        ? "EŞLEŞİYOR: Dosya özeti girilen değere eşit."
                        : "UYUŞMUYOR: Dosya özeti girilen değerden farklı.";
                message = "Boyut: " + result.bytes + " bayt\nSHA-256:\n" +
                    result.sha256 + "\n" + comparison +
                    "\nBu yalnızca yerel bayt bütünlüğü kontrolüdür.";
            } catch (IOException | SecurityException | IllegalArgumentException ignored) {
                message = "RET: Dosya okunamadı, erişim reddedildi veya 64 MiB sınırı aşıldı. Kaynak ya da gizli değer kaydedilmedi.";
            }
            runOnUiThread(() -> {
                if (isFinishing() || isDestroyed()) return;
                busy = false;
                choose.setEnabled(true);
                resultView.setText(message);
            });
        });
    }

    @Override
    protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }
}
