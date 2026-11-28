# PROJECT OMEGA — 100 Maddelik Uygulama Yol Haritası

**Sürüm:** 1.0  
**Oluşturulma:** 2026-11-28  
**Kaynaklar:** `AI_MASTER_ROADMAP.md` ve `docs/PROJECT_OMEGA_PHASE_0.md`

**Durum kuralı:** Tüm maddeler başlangıçta `[ ] YAPILACAK` durumundadır. Bir özelliğin kaynak belgede anılması, uygulandığı veya kabul testinden geçtiği anlamına gelmez. Kanıt olmadan `[x] TAMAM` yapılmaz.

## Yönetişim ve depo güvenliği

1. [ ] **YAPILACAK** — Depo kapsamı, sahiplik beyanı ve doğrulanmış yetki sınırlarını belgele.
2. [ ] **YAPILACAK** — Depo envanterini, runtime'ı, bağımlılıkları ve bilinmeyenleri güncelle.
3. [ ] **YAPILACAK** — Verileri public, internal, confidential ve restricted olarak sınıflandır.
4. [ ] **YAPILACAK** — Parola, token ve özel anahtarları Git, prompt, issue ve loglardan uzak tut.
5. [ ] **YAPILACAK** — Secret scanning'i kod ve PR diff'lerinde etkinleştir ve negatif test et.
6. [ ] **YAPILACAK** — Security-sensitive yollar için CODEOWNERS tanımla.
7. [ ] **YAPILACAK** — main için PR-only koruma ve zorunlu CI kurallarını etkinleştir.
8. [ ] **YAPILACAK** — Korunan dallarda force-push ve branch silmeyi engelle.
9. [ ] **YAPILACAK** — Lisans durumunu netleştir ve eksik lisans kararını kayda geçir.
10. [ ] **YAPILACAK** — Prompt injection, supply-chain ve yetki yükseltme tehdit modelini tamamla.

## Geliştirme ortamı ve yapılandırma

11. [ ] **YAPILACAK** — Desteklenen Python, Android ve build toolchain sürümlerini sabitle.
12. [ ] **YAPILACAK** — Yerel geliştirme önkoşullarını ve kurulum adımlarını belgele.
13. [ ] **YAPILACAK** — Tek komutlu geliştirici görevleri için Makefile veya eşdeğerini ekle.
14. [ ] **YAPILACAK** — Yalnızca placeholder içeren .env.example dosyasını doğrula.
15. [ ] **YAPILACAK** — Kritik ayarları doğrulayan ve hatalı yapılandırmayı reddeden loader ekle.
16. [ ] **YAPILACAK** — FastAPI uygulama giriş noktasını mimari karar sonrası kur.
17. [ ] **YAPILACAK** — Tüm API uçları için sürümlü istek/yanıt şemaları tanımla.
18. [ ] **YAPILACAK** — Yerel çalışma profilinde varsayılan ağ erişimini kapalı tut.
19. [ ] **YAPILACAK** — Bağımlılıkları kilitle ve güncelleme politikasını belgele.
20. [ ] **YAPILACAK** — Temiz ortamda tekrarlanabilir kurulum testi çalıştır.

## Backend ve API güvenilirliği

21. [ ] **YAPILACAK** — GET /api/health uç noktasını bağımlılık durumuyla uygula.
22. [ ] **YAPILACAK** — POST /api/chat uç noktasını sınırlandırılmış isteklerle uygula.
23. [ ] **YAPILACAK** — Provider anahtarlarını yalnızca sunucu tarafında tut.
24. [ ] **YAPILACAK** — İstek kimliği ve redakte edilmiş yapılandırılmış loglar ekle.
25. [ ] **YAPILACAK** — Outbound çağrılara bağlantı, okuma ve toplam timeout uygula.
26. [ ] **YAPILACAK** — Yalnızca retry edilebilir hatalara sınırlı backoff uygula.
27. [ ] **YAPILACAK** — Provider yoksa veya ayar bozuksa fail-closed davran.
28. [ ] **YAPILACAK** — Provider/model allowlist ve güvenli varsayılanları uygula.
29. [ ] **YAPILACAK** — Spoof-resistant rate limit ve body/message boyut sınırları ekle.
30. [ ] **YAPILACAK** — Stack trace ve secret sızdırmayan tutarlı hata yanıtları test et.

## Model altyapısı ve yönlendirici

31. [ ] **YAPILACAK** — Yerel model runtime seçimi için ADR hazırla.
32. [ ] **YAPILACAK** — Gerçek hedef donanımda yerel model benchmark'ı yap.
33. [ ] **YAPILACAK** — Ağ erişimi varsayılan kapalı yerel model adapter'ı geliştir.
34. [ ] **YAPILACAK** — Provider bağımsız model adapter arayüzü tanımla.
35. [ ] **YAPILACAK** — Fast/default model yönlendirme kurallarını deterministik yap.
36. [ ] **YAPILACAK** — Reasoning model rotasını kapasite ve maliyet sınırlarıyla ekle.
37. [ ] **YAPILACAK** — Coding model rotasını bağlam ve çıktı sınırlarıyla ekle.
38. [ ] **YAPILACAK** — Vision rotasını yalnızca açıkça yetkilendirilmiş girdilerde aç.
39. [ ] **YAPILACAK** — Fallback kurallarının policy atlamadığını garanti et.
40. [ ] **YAPILACAK** — Model seçimi ve routing kararını secret içermeyen logla.

## Web araştırma ve retrieval

41. [ ] **YAPILACAK** — Server-side web research adapter'ını feature flag arkasında kur.
42. [ ] **YAPILACAK** — Her araştırma sonucu için kaynak URL ve retrieval timestamp sakla.
43. [ ] **YAPILACAK** — Kaynak allow/deny kuralları ve sonuç sınırları ekle.
44. [ ] **YAPILACAK** — Fetch timeout ve açık offline/unavailable durumu uygula.
45. [ ] **YAPILACAK** — Provider başarısızlığında uydurma citation üretimini engelle.
46. [ ] **YAPILACAK** — Kaynak içeriğini güvenilmeyen veri olarak ele al.
47. [ ] **YAPILACAK** — Prompt injection içeren sayfalarla adversarial test yaz.
48. [ ] **YAPILACAK** — Doküman erişim kontrolü olan retrieval API tasarla.
49. [ ] **YAPILACAK** — Incremental indexing ve deterministik güncelleme/silme davranışı ekle.
50. [ ] **YAPILACAK** — Kaynak gösterimli retrieval doğruluk testleri çalıştır.

## Sahip kimliği ve kriptografik güvenlik

51. [ ] **YAPILACAK** — E-posta veya telefonun tek başına kimlik kanıtı olmadığını tasarıma işle.
52. [ ] **YAPILACAK** — Android Keystore üzerinde asimetrik owner key üret.
53. [ ] **YAPILACAK** — Platform destekliyorsa private key'i non-exportable tut.
54. [ ] **YAPILACAK** — Owner kimliğini onaylı cihazla kriptografik olarak bağla.
55. [ ] **YAPILACAK** — Yüksek riskli eylemlerde biyometri veya cihaz kimliği iste.
56. [ ] **YAPILACAK** — Nonce ve expiry kullanan signed challenge-response uygula.
57. [ ] **YAPILACAK** — Replay, expired ve hatalı imzalı komutları reddet.
58. [ ] **YAPILACAK** — Key revoke, cihaz değişimi ve recovery prosedürü geliştir.
59. [ ] **YAPILACAK** — Owner state'i at-rest şifrele ve backup sınırlarını tanımla.
60. [ ] **YAPILACAK** — Owner, non-owner, revoked-key ve replay testlerini geçir.

## Android köprüsü ve görev yürütme

61. [ ] **YAPILACAK** — Android bridge sınırını PWA/backend'den ayrı tanımla.
62. [ ] **YAPILACAK** — Observe-plan-act-verify görev yaşam döngüsünü uygula.
63. [ ] **YAPILACAK** — Her cihaz eyleminden önce allowlisted plan doğrula.
64. [ ] **YAPILACAK** — Accessibility kullanımını açıkça yetkilendirilmiş akışlarla sınırla.
65. [ ] **YAPILACAK** — Shizuku, ADB veya root yetkisini sessizce yükseltme.
66. [ ] **YAPILACAK** — Her eylem sonrası cihaz postcondition doğrulaması yap.
67. [ ] **YAPILACAK** — Her işlem için cancellation, timeout ve safe-stop ekle.
68. [ ] **YAPILACAK** — Redakte edilmiş audit event üret.
69. [ ] **YAPILACAK** — Cihaz bağlantısı kesilmesi ve kısmi yürütme testleri yaz.
70. [ ] **YAPILACAK** — Gerçek cihazda kritik akışların kabul testini çalıştır.

## Veri katmanı ve Türkçe UI

71. [ ] **YAPILACAK** — PostgreSQL kararını şema ve operasyon gereksinimleriyle doğrula.
72. [ ] **YAPILACAK** — Task ve audit metadata için versioned migrations ekle.
73. [ ] **YAPILACAK** — Permission-filtered indexing ve retrieval sınırlarını uygula.
74. [ ] **YAPILACAK** — Vector/search store seçimini benchmark'a bağla.
75. [ ] **YAPILACAK** — Backup ve restore prosedürlerini uygula.
76. [ ] **YAPILACAK** — Cross-user ve cross-scope retrieval denial testleri yaz.
77. [ ] **YAPILACAK** — Türkçe yönetim arayüzünde task ve authorization durumunu göster.
78. [ ] **YAPILACAK** — Approve, reject, cancel ve stop kontrolleri ekle.
79. [ ] **YAPILACAK** — Planned/running/passed/failed/unverified durumlarını ayır.
80. [ ] **YAPILACAK** — UI erişilebilirlik ve API hata durumlarını test et.

## Test, CI/CD ve tedarik zinciri

81. [ ] **YAPILACAK** — Policy, authorization, routing ve task state unit testleri ekle.
82. [ ] **YAPILACAK** — API, database ve adapter entegrasyon testleri yaz.
83. [ ] **YAPILACAK** — Browser acceptance testlerini kritik akışlara ekle.
84. [ ] **YAPILACAK** — Prompt injection ve untrusted repository içeriği testleri ekle.
85. [ ] **YAPILACAK** — Dependency vulnerability review ve pinned update süreci kur.
86. [ ] **YAPILACAK** — Release candidate için SBOM üret.
87. [ ] **YAPILACAK** — GitHub Actions kullanımlarını mümkün olduğunca immutable SHA'ya sabitle.
88. [ ] **YAPILACAK** — Her workflow için least-privilege GITHUB_TOKEN permissions uygula.
89. [ ] **YAPILACAK** — Lint, unit, integration ve privacy/secret check CI kapıları kur.
90. [ ] **YAPILACAK** — Zorunlu kontrol veya kanıt eksikse release'i engelle.

## İmzalı sürüm, operasyon ve kabul

91. [ ] **YAPILACAK** — Android release artifact'ını kayıtlı source commit SHA'dan üret.
92. [ ] **YAPILACAK** — İmzalama anahtarını korumalı secret store ve rotation planıyla yönet.
93. [ ] **YAPILACAK** — APK/AAB signature ve certificate fingerprint doğrula.
94. [ ] **YAPILACAK** — Her release artifact için SHA-256 hesapla ve yayımla.
95. [ ] **YAPILACAK** — Source SHA, workflow run, artifact ve signer provenance bağını kur.
96. [ ] **YAPILACAK** — Staging smoke testini fiziksel desteklenen Android cihazda çalıştır.
97. [ ] **YAPILACAK** — Install, launch, upgrade ve izin akışlarını cihazda test et.
98. [ ] **YAPILACAK** — Staging rollback provası yap ve kanıt makbuzunu sakla.
99. [ ] **YAPILACAK** — Play Billing purchase, restore, cancel, refund ve replay akışlarını test et.
100. [ ] **YAPILACAK** — Incident response, health monitoring, backup/restore ve bağımsız kabul kanıtlarını tamamla.

## Tamamlanma ölçütü

Bir madde ancak ilgili kod/değişiklik, başarılı otomatik test veya gerçek ortam kanıtı ve gözden geçirilebilir kaynak bağlantısı mevcutsa tamamlanabilir. Tasarım belgesi, mock, preflight veya yalnızca CI'ın başlamış olması fiziksel cihaz/deployment kabulü yerine geçmez.

## Kritik güvenlik kapıları

- Restricted secrets yalnızca GitHub Actions Secrets veya eşdeğer korumalı secret store içinde tutulur.
- Bilinmeyen yetki varsayılmaz; yıkıcı işlemler ve üretim değişiklikleri uygun onay kapısına tabidir.
- Fiziksel cihaz, staging deployment, rollback ve Billing kanıtları gerçek ortamdan alınır.
- Üretime hazır olma beyanı ancak tüm zorunlu kabul kapıları geçildiğinde yapılır.


---

# MÜFETTİŞ 7. TUR — YENİ HEDEFLER VE KANITLI İCRA EKİ

**Sürüm:** 1.1  
**Tarih:** 2026-11-28  
**Kapsam:** Aşağıdaki dört iş paketi, mevcut 100 maddenin kapsamını genişletir. Ana 100 maddelik numaralandırma korunur. Bu ek, özelliklerin tamamlandığı anlamına gelmez.

## A. Google Play tahsilat, mutabakat ve payout

### Değişmezler
- Mevcut Play Console ödeme profili, banka hesabı, ürün kimlikleri, abonelikler, fiyatlar ve kullanıcı hakları açık kullanıcı onayı olmadan değiştirilmez.
- Google Play tahsilatı ile geliştirici payout aktarımı iki ayrı işlem olarak modellenir.
- Google Play satışlarında Google'ın merchant payout mekanizması esas alınır. Play Billing uygulama kodu banka hesabına para göndermez.
- RevenueCat, abonelik doğrulama/entitlement ve olay senkronizasyonu için kullanılabilir; Google Play geliştirici payout'unu kendi başına başka banka hesabına yönlendirmez.
- Stripe, Play Store üzerinden alınmış siparişlerin payout yöneticisi gibi kullanılmaz. Stripe ancak uygulamanın ayrı ve Google Play politikalarına uygun harici ödeme akışı varsa değerlendirilir.
- Payout banka hesabı değişikliği, ödeme profili güncellemesi ve finansal sağlayıcı ayarları yalnızca hesap sahibinin ilgili konsolda yaptığı açık işlem ve doğrulamasıyla yürütülür.

### Uygulama iş paketleri
1. Mevcut Play Console merchant/payment profile, ülke, para birimi, payout takvimi ve banka hesabı yapılandırmasını salt-okunur envanterle belgelemek.
2. Play Billing ürün/abonelik kataloğunu mevcut ürün kimlikleriyle eşleştirmek; hiçbir SKU veya fiyatı değiştirmemek.
3. Android istemcide purchase token, order ID, product ID ve purchase state alanlarını güvenli şekilde backend'e iletmek.
4. Backend'de Google Play Developer API doğrulamasını servis hesabı ve minimum gerekli API kapsamlarıyla tasarlamak.
5. Real-time developer notifications (RTDN) olaylarını Pub/Sub üzerinden almak; olayları idempotent işlemek ve Play Developer API ile durum teyidi yapmak.
6. Satın alma, yenileme, iptal, grace period, account hold, refund ve revoke durumları için değişmez audit ledger kurmak.
7. Payout raporlarını ve banka ekstresi mutabakatını salt-okunur içe aktarma/raporlama katmanında modellemek.
8. Uygulama içinde payout başlatma veya banka hesabı değiştirme endpoint'i açmamak. Google Play merchant payout akışını uygulama backend'inden taklit etmemek.
9. Gerçek para transferi gerektiren başka bir sağlayıcı seçilirse lisans/ülke uygunluğu, KYC, AML, webhook imza doğrulaması, settlement ve chargeback süreçlerini ayrı proje kararı olarak değerlendirmek.
10. Sandbox/test hesaplarıyla uçtan uca test; üretim finansal ayar değişikliği yapmadan kabul kanıtı toplamak.

### Kabul kanıtı
- Play Console'dan mevcut ödeme profili ve payout yöntemi değişmeden önce/sonra karşılaştırma kaydı.
- Play Billing test purchase ve server-side token doğrulama çıktısı.
- RTDN imza/kimlik doğrulama, duplicate delivery, gecikmiş olay, refund/revoke ve idempotency testleri.
- Mutabakat raporu; banka hesap numarası veya hassas finansal veri loglara yazılmaz.
- Gerçek payout yalnızca Google Play Console'un resmi finansal raporları ve banka ekstresiyle doğrulanır.

**Başlangıç durumu:** YAPILACAK. Bu depoda mevcut Play merchant payout ayarlarının veya banka hesabının değiştirildiğine dair kanıt yok. Kod, Google'ın payout sisteminin yerine geçemez.

## B. OMEGA AI — imzalı sahip yetkilendirmesi ve veri erişim köprüsü

### Güvenlik mimarisi
1. Model talimatı tek başına yetki kaynağı sayılmaz. Yetki, sunucu tarafında doğrulanan cihaz/sahip anahtarları ve izin politikasıyla verilir.
2. Mevcut KRAL çift P-256 imza, nonce/replay koruması ve yerel salt-okunur işçi yaklaşımı yeniden kullanılabilir; OMEGA'ya taşınmadan önce kod ve testler yeniden incelenir.
3. Özel anahtar Android Keystore veya eşdeğer korumalı donanım/OS anahtar kasasında tutulur; mümkün olduğunda dışa aktarılamaz.
4. Her komut canonical request, nonce, expiry, cihaz kimliği ve kapsamı ile imzalanır.
5. Prompt injection, jailbreak ve araç çıktısı manipülasyonu güvenilmeyen veri olarak sınıflandırılır. Bunlar izin, rol veya policy değiştiremez.
6. Model yalnızca plan önerir. Her araç çağrısı ayrı policy enforcement katmanından geçer.
7. İlk sürüm salt-okunur GitHub/Drive/Play veri erişimiyle sınırlıdır. Yazma, ödeme, merge, silme, release ve payout işlemleri ayrı izin ve kullanıcı onayı gerektirir.
8. Tokenlar secret store'da tutulur; repo, prompt, model bağlamı ve loglara konmaz. OAuth kapsamları en az yetkiyle sınırlandırılır.
9. Her veri kaynağı için erişim denetimi, token yenileme/iptal, audit izi ve erişim kesme prosedürü kurulur.
10. Kaynak dokümanlar ve web içerikleri komut değil veri olarak işlenir; veri sızıntısı ve cross-scope retrieval testleri uygulanır.

### Veri bağlayıcıları
- GitHub: başlangıçta seçilmiş depolar için read-only metadata, contents ve workflow/artifact okuma izinleri. PR merge, branch yazma ve secret erişimi varsayılan kapsam dışıdır.
- Google Drive: Google OAuth ile yalnız seçilen dosya/klasörlere read-only erişim. Drive connector veya API erişimi kurulmadan erişim varmış gibi davranılmaz.
- Google Play: Play Developer API salt-okunur rapor/abonelik doğrulama kapsamları. Merchant ödeme profili ve banka hesabı yönetimi ayrı konsol işlemi olarak kalır.

### Kabul kanıtı
- Geçerli sahip/cihaz imzası kabul edilir; yanlış imza, süresi geçmiş nonce, tekrar oynatma ve iptal edilmiş anahtar reddedilir.
- Prompt injection metni araç izinlerini değiştiremez.
- GitHub/Drive/Play erişimleri yalnız izin verilen kaynak ve kapsamda çalışır.
- Token değerleri hiçbir test çıktısında veya logda görünmez.
- Yetkisiz yazma/ödeme/silme/merge girişimleri fail-closed reddedilir.

**Başlangıç durumu:** KISMİ TARİHSEL KANIT VAR; OMEGA entegrasyonu ve gerçek anahtar kaydı YAPILACAK.

## C. 100 maddenin geçmiş kanıt denetimi

Denetim yöntemi:
- Mevcut main dosyası ve erişilebilir depo envanteri başlangıç noktasıdır.
- Açık/kapalı PR açıklamaları, diff'ler, merge commitleri, workflow kanıtları ve kaynak dosyalar birbirinden ayrılır.
- Bir PR'ın kapalı olması veya kodun başka bir dala merge edilmesi, OMEGA main üzerinde tamamlanma anlamına gelmez.
- Tasarım belgesi, sentetik test ve CI sonucu gerçek cihaz, üretim veya banka payout kanıtı yerine sayılmaz.
- Her maddeye yalnızca doğrudan eşleşen kanıt ve kabul ölçütü tamamlanma işareti verebilir. Kanıt yoksa YAPILACAK kalır.

### İlk bulunan tarihsel kanıtlar
| Kaynak | Kanıtlanan kapsam | Tamamlanmayan sınır |
|---|---|---|
| https://github.com/mehmetcerdik457-ctrl/Gpt-asistan/pull/72 | Çift P-256 sahip/cihaz imzası, tek kullanımlık nonce, SQLite WAL, idempotency, sınırlı salt-okunur yerel worker endpoint'i; PR merge edilmiş | Hedef dalı OMEGA main değil, entegrasyon dalıdır. Gerçek owner/device key enrollment, canlı model ve gerçek cihaz kabulü ayrıca gerekir. |
| https://github.com/mehmetcerdik457-ctrl/Gpt-asistan/pull/88 | APK imzalama pipeline'ı, sertifika pini, exact-source provenance ve artifact/test raporları | PR açıklamasında gerçek owner signing BLOCKED_OWNER_SECRETS_MISSING olarak raporlanmıştır; debug APK sahip imzalı release değildir. |
| https://github.com/mehmetcerdik457-ctrl/Gpt-asistan/pull/73 | APK build kaynağını PR head SHA / push SHA ile eşleştiren exact-source kontrolü | Bu kanıt gerçek cihaz kurulum/upgrade veya Play kabulü değildir. |

**Denetim sonucu (bu ekin yazıldığı anda):** 100 maddenin tamamı tek tek kanıtlanıp yeniden sınıflandırılmış değildir. Bu yüzden doğrulanmış tamamlanma sayısı henüz ilan edilmez. Yukarıdaki tarihsel bileşenler, ilgili maddeler için yeniden inceleme adayıdır; otomatik olarak TAMAMLANDI sayılmaz.

## D. Yayın ve demo videosu senaryosu

### Çekim öncesi
1. Test cihazının modelini, Android sürümünü, uygulama versionName/versionCode ve kaynak commit SHA'sını kaydet.
2. Yalnızca test hesabı ve Play test track/test product kullan. Gerçek para ile satın alma yapma.
3. Uygulama imza sertifikası, APK SHA-256 ve yüklenen artifact kaydını hazırla.
4. Ekran kaydında e-posta, telefon, banka bilgisi, token, satın alma makbuzu ve özel bildirimleri gizle.
5. Ağ bağlantısı, backend ve model durumunu test başlamadan not et; başarısız denemeleri videodan kesip başarılıymış gibi sunma.

### Kayıt akışı
1. Uygulamayı temiz açılışla başlat; sürüm ve cihaz bilgisi ekranını göster.
2. Ana ekranı ve temel gezinmeyi göster.
3. Hesap/izin ekranında kullanıcıya sunulan izinleri açıkla; izinsiz sistem erişimi olmadığını göster.
4. AI sohbet ekranında zararsız bir test sorusu sor; yanıtın kaynak/model durumunu ve hata halinde dürüst unavailable davranışını göster.
5. Prompt-injection güvenlik testinde, güvenilmeyen bir metnin gizli veri veya araç yetkisi talebini reddettiğini göster.
6. Yerel görev ekranında yalnızca izinli salt-okunur bir görev çalıştır; audit kaydı ve görev sonucunu göster.
7. Play Billing test ürününü seç; Google Play test satın alma onay ekranını göster.
8. Satın alma token'ının backend'de doğrulandığını, entitlement durumunun güncellendiğini ve duplicate webhook'un ikinci hak/işlem oluşturmadığını göster.
9. Test aboneliğinin iptal/yenileme/refund durumunu sandbox/test raporunda göster.
10. Payout bölümünde yalnız raporlama ve mutabakat ekranını göster. Banka hesabı değiştirme veya gerçek para transferi yapılmadığını açıkça belirt.
11. Ayarlar, gizlilik, çıkış ve uygulamayı yeniden açma akışlarını göster.
12. Videonun sonunda test sonucu, bilinen kısıtlar, build SHA ve artifact hash'ini ekranda veya açıklamada yayımla.

### Demo kabul matrisi
| Alan | Başarı koşulu | Kanıt |
|---|---|---|
| Kurulum/açılış | Desteklenen cihazda çökmeden açılır | Ekran kaydı + cihaz log özeti |
| AI | Yanıt, hata ve unavailable davranışı doğru | Test promptları + audit event |
| Güvenlik | Geçersiz imza/replay/injection reddedilir | Negatif test raporu |
| Billing | Test purchase doğrulanır, entitlement tekilleşir | Play test + backend ledger |
| Abonelik | Cancel/refund/revoke durumu doğru yansır | Test olayları |
| Payout | Finansal ayarlar değişmeden rapor/mutabakat gösterilir | Konsol raporu, hassas alanlar maskeli |
| Release | Kaynak SHA, imza sertifikası ve APK hash eşleşir | İmzalama raporu |

**Başlangıç durumu:** SENARYO HAZIR; gerçek cihaz çekimi ve canlı özellik kanıtı YAPILACAK.

## Tur 7 icra notu
Bu ek, mevcut 100 maddeyi tamamlandı olarak işaretlemez ve hiçbir Play Console, banka, ödeme profili, secret veya üretim ayarını değiştirmez. Yeni kodlama işleri, önce mevcut mimari ve ilgili dosyalar doğrulandıktan sonra ayrı küçük değişiklikler ve testlerle uygulanacaktır.
