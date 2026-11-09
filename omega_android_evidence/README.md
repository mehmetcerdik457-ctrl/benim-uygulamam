# OMEGA S10 — çevrimdışı Android kanıt denetçisi

**Durum: deneysel DEBUG istemci; gerçek KRAL/OMEGA üretim APK'sı değildir.**
Bağımsız Android kaynak kodu, mevcut [Sohbet 10 PR #97](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/pull/97) üzerine stacked, mevcut FastAPI/PostgreSQL/PWA koduna dokunulmadı.

## Gerçekten yaptığı

Android belge seçiciden **yalnızca kullanıcının seçtiği bir dosyanın** okuma akışını alır. 64 MiB güvenli sınırda SHA-256 hesaplar ve kullanıcı 64 haneli beklenen özeti girerse sabit zamanlı karşılaştırır. Dosyayı uygulama deposuna kopyalamaz, ağ üzerinden göndermez, kalıcı erişim izni istemez. Ana ekranda boyut, SHA-256 ve eşleşme sonucunu gösterir. Arka planda tek worker ile çalışır; pencere ekran görüntüsü `FLAG_SECURE` ile korunur.

- Manifest: `INTERNET`, `CAMERA`, `RECORD_AUDIO`, konum ve geniş dosya izinleri **yok**.
- Android minimum API 26, compile/target API 35; `org.omega.offline.evidence` ayrı uygulama kimliği.
- Dış Android bağımlılığı yok; Android SDK ve Gradle derleme araçları, JUnit4 sadece test.
- Uygulama internete bağlanamaz, OMEGA Owner/API hesabına giriş yapmaz, yerel modeli çalıştırmaz, kodu uzaktan yürütmez, GitHub/Drive'a erişmez.
- Token, gizli anahtar, şifre, kayıtlı sohbet, veritabanı, geri yükleme veya cihaz kimliği yok.
- `debug` imzası GitHub runner üzerinde geçici Android debug anahtarı ile üretilebilir; **Play Store imzası ya da güvenilir sürüm yükseltme anahtarı değildir**.

## Bütünlük ≠ güvenilir köken

Dosyanın SHA-256 özeti ancak beklenen özet **bağımsız, güvenilir bir kanaldan** gelmişse işe yarar. Hash'in eşleşmesi, dosyanın zararsızlığını, gerçek üreticisini veya orijinal OMEGA 100 şartnamesinin sağlandığını kanıtlamaz. Daha eski `0.1.4-dev` ve `0.1.5` özel yedekleri **bu dalda yok**, hiçbir özel dosya okunmadı. İlgili beklenen hash veya dosya başka kaynaktan otomatik getirilmez.

## Oluşturma ve kabul

`.github/workflows/omega-s10-android-evidence.yml` yalnız bu Android alt projesini işler; Android Gradle Plugin 8.9.2 ve Gradle 8.11.1, Java 17, compileSDK 35 kullanır. JUnit4 `EvidenceHasherTest` kodu bilinen hash, tam boyut sınırı, fazla boyut reddi, biçim ve eşleşme sonuçlarını kontrol eder. Ardından lint/assembleDebug, APK debug imza doğrulama, manifestte **sıfır uses-permission** kontrolü ve SHA-256 üretimi yapılır. İndirilebilir GitHub Actions artefaktı oluşturulur.

**Üretim kabul engelleri:** bağımsız kod inceleme, cihazda Android 17/14/15 testleri, sistem belge seçici ve erişilebilirlik/TalkBack testleri, Android API 36+ yükseltme, tasarım, production keystore ile owner tarafından imzalanmış release, sürüm yükseltme kanıtı, tek KRAL uygulamasına entegrasyon, gerçek OIDC/Owner enrollment ve OMEGA API kapsamlarının güvenli doğrulanması. Bunlar olmadan **APKA-09/10 ve OMEGA-79/80 TAM kabulü verilmez**.

CI yeşil olsa bile **Android APK dosyası GitHub Actions artefaktında kanıtlanmadıkça teslim edilmiş sayılamaz**. Gerçek imzalı release, Play Store, otomatik telefona kurulum veya gerçek hesap bağlantısı yok. Ana dal değiştirilmemeli.
