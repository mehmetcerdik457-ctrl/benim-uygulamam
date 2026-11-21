# PROJECT OMEGA — 100 Adımlık Yol Haritası / Birebir Karşılaştırma Raporu

Hazırlanma: 2026-11-21 (bu oturum, salt-okunur doğrulama; hiçbir üretim onayı verilmedi)

## 1. Resmî kabul kapısı durumu (formal)

| Kaynak | Durum |
| --- | --- |
| `evidence/omega-100-acceptance.json` (OMEGA-001..100) | **100/100 BLOCKED** — her madde için genel gerekçe: bağımsız madde-başı kabul kanıtı, sahip yetkilendirmesi ve üretim entegrasyonu doğrulanmadı |
| `scripts/omega_acceptance_gate.py --enforce` | Tasarım gereği **exit 1** (VERIFIED kanıt + auditor/sahip Ed25519 çifte imza yok) |
| Spec kataloğu bağlama | `omega-100-spec-fingerprints.json` — 100/100 madde özgün v2.0 şartname metniyle birebir SHA-256 eşleşmeli; uyumsuzluk: 0; katalog kilit SHA `d5a3a415efbf...49824fc` |
| PR #105 bugünkü doğrulama | Exact HEAD `97cbc027` CI yeşil (4 run) + lokal **57/57 OK** + deny-only PASS |

**Karar kapısı:** "Yüz adımlık yol haritası bitti mi?" → **HAYIR.** Kapı 100/100 BLOCKED; bu ekibe/işe atanan makine tarafından üretilip imzalanacak kanıtla değişmez — üretim kanıtı zaten yalnızca sahip tarafında (cihaz, sır, imza) bulunabilir.

## 2. Bilinen son madde-çapraz toplamı (13 Eki 2026, OMEGA 16 bütünlük denetimi)

| Taban | TAM | KISMİ | YAPILMAMIŞ | Not |
| --- | --- | --- | --- | --- |
| Özel 0.1.4-dev | **42/100** | **55/100** | **3/100** | Madde-çapraz etiket verilmemiş; toplamlar dışında çıkarım yasak |
| Kamu GitHub | 0 DONE | 21 PARTIAL | 78 NOT_STARTED (+1 BLOCKED) | Madde-başı etiket icat edilmemesi kuralı geçerli |

PR #69 entegrasyon nosyonu: 10 uzman PR'ından 91 ayrık dosya → tek HEAD `88ace179`; exact-SHA offline suite **605 passed / 19 skipped** ([run 38345282050](https://github.com/mehmetcerdik457-ctrl/benim-uygulamam/actions/runs/38345282050)); PostgreSQL E2E 36/36; tek zorunlu PR başarısızlık: Docker runner-host gate (`OMEGA_RUNNER_HOST_VERDICT=BLOCKED_NOT_ACCEPTED`).

## 3. 13 Eki → 21 Nov arası eklenen VE doğrulanan ilerleme (birleştirme girdisi)

### benim-uygulamam (OMEGA kontrol düzlemi)
- **Merge #99** (11 Nov): P-256 imzalı owner chat + fail-closed gateway testleri
- **Merge #106** (17 Nov): redacted backend pre-deploy failure checks
- **PR #101** (açık draft, main'e): 100/100 kabul kapısı; 7 kontrol SUCCESS + deny-only tasarım; MERGEABLE
- **PR #105** (açık draft, #101 üstüne istifli): attestation + tam SHA'lı CI; **21 Nov'da bu oturumca exact-head 4 run SUCCESS + lokal 57/57 yeniden doğrulandı**
- Açık güvenlik/AST/Türkçe panel zinciri: PR #87–#100 (draft, CH TEST'li)

### Gpt-asistan (KRAL/Android)
- **Merge #71, #72, #73** (1 Nov): offline autonomy (WAL, hybrid memory, idempotent owner chat), Genesis 3.0 Sol allowlist + dual-P256 worker, APK provenansı exact-SHA'ya kilitlenme
- **Merge #88** (4 Nov): KRAL Android 1.0.6 — pinned owner-signing path + verified APK delivery
- **Merge #93** (5 Nov): OTP hardcoded e-posta temizliği + fail-closed
- **Draft zinciri #116→#132** (11→20 Nov): CI kanıtları Issue #25'te şaşmaz exact-SHA + run ID mantarıyla: 330→356→360→387→413→442 Python PASS; `:app:bundleRelease` SUCCESS; bundletool ile 4 cihaz profili (API26/30/36) × 5 APK split testi imza tutarlı PASS
- **Bu oturum (21 Nov):** integration dalı `c5ff163` lokal 45/45 OK + CI 2/2 SUCCESS yeniden teyit; PR #132 `studio-pipeline` FAILURE kök nedeni (ölü test videosu + JS runtime yok) bulundu, **fix hazır** (`fix/studio-pipeline-fixture` dalında: `jNQXAC9IVRw` + `--js-runtimes node`); PR #131 build/emulator failure = kaldırılmış Kotlin 1.9.22 transitifleri (toolchain), release failure = eksik Actions secrets

### Diğer kaynaklar
- **Slack:** OMEGA/KRAL/ORBA kaydı yok (aramalar boş).
- **Drive (kanıt arşivi 1GQPrI2…):** erişim hâlâ provision edilmemiş → kanıt arşivine bakılamadı (bilinçli BLOCKED).
- **Linear:** YAP-5..26 kayıtları; son 2 ayda 7 açık issue, 7/7 tamamlanmamış.

## 4. Adım-başı durum tablosu (yalnızca doğrulanabilir gerçekte kod+CI kanıtı olanlar; metinler yalnızca SHA olarak var olduğundan üretimden değil iyileştirmeden konuşulur)

| FAZ | Kapsam | Kanıt durumu 21 Nov |
| --- | --- | --- |
| FAZ 0 (1–10) | Keşif + yönetim | Faz 0 dokümanı + scope.yaml + ADR + kabul kapısı mekanizması hazır; envanter raporu bu oturumda tamamlandı |
| FAZ I (11–20) | Dijital envanter/güvenli veri | PR #60/#61 içindeki kod; canlı GitHub/Drive kanıt taraması yok (LIVE_ACCESS_UNKNOWN) |
| FAZ II (21–30) | Kasa + kimlik | Owner crypto P-256 chat **merge'lendi** (#99); HMAC/Ed25519 attestation PR #105 hazır; gerçek keystore cihaz kanıtı yok |
| FAZ III (31–40) | Bilgi katmanı + uzun hafıza | kral_memory + hybrid retrieval WAL persist **merge'lendi** (#71); PostgreSQL gerçek DB entegrasyonu (YAP-23) backlog |
| FAZ IV (41–50) | Yerel YZ + model router | PR #63/#68; model allowlist fail-closed PR #91; gerçek cihaz benchmark yok |
| FAZ V (51–60) | Orkestrasyon çekirdeği | PR #63 orkestrasyon kodu + PR #101 kapı mekanizması; gerçek IdP/OIDC yok |
| FAZ VI (61–70) | Copilot + kod denetimi | PR #66;çöplerin tümü draft; Copilot görev devri kanıtlanamadı (BLOCKED) |
| FAZ VII (71–80) | Türkçe web paneli | PR #66/#97 Türkçe güvenlik ekranları; panel UI/API testleri run 38345281909 SUCCESS |
| FAZ VIII (81–90) | Güvenli otonomi + kalite | PR #67; Sentroll setUp WAL runner host Docker gate FAILURE (BLOCKED_NOT_ACCEPTED) |
| FAZ IX (91–100) | Üretim + gözlemlenebilirlik | PR #67; owner BACKUP/restore, gerçek Grafana, canlı billing 476/457, gerçek cihaz: NOT_RUN/BLOCKED |

## 5. Kapanışta gerekenler (büyük çoğunlukla SAHİP tarafı — kod değil)

1. GitHub yazma izinleri (App/PAT scope genişletme) → `fix/studio-pipeline-fixture` push + PR #132 fix, PR evidence yorumları
2. Actions secrets: `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` (PR #131 release)
3. Kotlin/AGP toolchain güncellemesi (PR #131 build/emulator; kaldırılmış 1.9.22 transitifleri)
4. Drive + Google Cloud provisioning (YAP-24/25, kanıt arşivi, MM/DD 476/457 canlı kanıt)
5. Gerçek cihaz test matrisi + StrongBox/biometrik runtime gate (YAP-9/YAP-11)
6. Owner + bağımsız auditor Ed25519 anahtar tedariki ve madde-başı imzalı kanıt üretimi (kabul kapısının 100/100 VERIFIED'tan geçebilmesi için)
7. Kadı runner-host Docker gate kök nedeni: daemon incelemesi (run 38345281975)

## 5b. 21 Nov oturumu 2. tur — kök neden incelemesi tamamlandı (ek)

**Eşik 3 (PR #131 build/emulator):** `Could not find kotlin-reflect:1.9.22 / kotlin-stdlib:1.9.22 / org.jetbrains:annotations:13.0` hatasının artefakt-kaldırma tezi ÇÜRÜTÜLDÜ — dördünün POM'u bu oturumda Maven Central'dan HTTP 200 ile erişilebilir (kök dalda plugin versiyonu zaten 1.9.24). Hata ortamsal/geçici; kod düzeltmesi YOK, tek çare CI rerun (izin bekliyor; rerun 403).

**Eşik 7 (Docker runner-host gate, run 38345281975):** Kök neden netçesine bulundu:
- `OMEGA_DOCKER_PORT_REQUESTED=LOOPBACK_ONLY`
- `OMEGA_DOCKER_PORT_EFFECTIVE=MISSING`
- `OMEGA_DOCKER_PORT_CAUSE=DOCKER_REQUEST_ACCEPTED_BUT_PUBLICATION_NOT_EFFECTIVE`
- `OMEGA_RUNNER_HOST_TCP=REFUSED`, `OMEGA_RUNNER_HOST_HTTP=BLOCKED`
- Ama `OMEGA_DIRECT_HOST_VERDICT=PASS_DIRECT_HOST_TO_INTERNAL_NOT_LOOPBACK_OR_OWNER`

Yorum: Docker API'sı yalnızca-loopback port yayını isteğini KABUL ediyor; ama GitHub-owned runner'da (VM içinde nested docker) bu yayın host'a ETİKİ GERÇEKLEŞMİYOR. Gate doğru çalışıyor: hosted CI'da bu kabulün geçmesi mümkün değil — tasarım gereği yalnızca SAHİP MAKİNESİNDE PASS edebilir. Hosted CI'daki bu iş “EXPECTED_BLOCKED_ON_HOSTED_CI” olarak işaretlenmeye aday; sahibin host kabullerinde ise asıl kanıt yeri bu.

**Yeni engel notu:** `curl` sandbox'a kapalı → Maven doğrulaması web_fetch/python urllib ile yapıldı (HTTP 200 kanıtlanabilir); sandbox'ta sudo yok → JDK/Gradle kurulumlu tam lokal tekrar mümkün değil; PR #131 için lokal derleme doğrulaması yapılamadı (CI rerun'ı beklemede).

## 6. Hücuma kapı yönetimi (bu oturumda denenen ve reddedilenler)

- `git push` → 403 `Permission ... denied` (Gpt-asistan ve benim-uygulamam)
- PR/issue yorum (gh + GitHub App connector) → 403
- Workflow rerun → 403 "cannot be rerun"
- Branch protection okuma → 403
- Bu nedenle hiçbir üretim/merge/broadening eylemi yapılmadı; `unknown_permissions_are_denied: true` kuralı korundu.
