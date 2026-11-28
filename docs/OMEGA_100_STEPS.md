> **Çapraz-depo denetim notu — 2026-11-28**  
> Bu yol haritası PROJECT OMEGA içindir. KRAL Android uygulamasının `mehmetcerdik457-ctrl/Gpt-asistan` deposundaki PR ve APK/AAB kanıtları OMEGA adımlarını otomatik tamamlamaz; bu nedenle aşağıdaki 100 maddenin checkbox durumları kanıt olmadan değiştirilmemiştir.  
> - KRAL PR #72 ve #88 kapalı/birleştirilmiş durumdadır; hedef dalları sırasıyla `integration/kral-asistan-20261020` ve `fix/kral-genesis-android-delivery-20261103`, **main değildir**.  
> - KRAL PR #99 ve #104 açık/taslak durumundadır. #99 exact-head CI kayıtları başarılıdır; #104 exact-head CI kayıtları atlanmıştır. Bu nedenle bu dört PR'ın main'e entegre edildiği veya kabul kapılarının geçtiği iddia edilmez.  
> - 2026-11-28 KRAL `Signed Android Release` run `46116604566` APK/AAB üretmiştir. APK SHA-256: `b4628df3f25aac54ad631aa3258ba1f83cf71febfaadf4db75684c69535980a1`; AAB SHA-256: `adb417b455da9358471e8e50290c23c97b4eef2fc22adfe16c5762e41316918f`. Bu çıktılar KRAL deposuna aittir, OMEGA release kanıtı değildir.  
> - KRAL APK manifesti `minSdk=24`, `targetSdk=34`, `versionCode=1`, `versionName=1.0.0` gösterir. 2026-08-31 itibarıyla yeni Play uygulaması/güncellemesi için API 36 gerektiğinden bu APK Play gönderimine uygun değildir. APK/AAB sertifika SHA-256 parmak izi eşleşir; Play Console paket eşleşmesi ve gerçek yükleme kontrolü yapılmamıştır.  
> - GitHub Releases asset yükleme/Release oluşturma bu oturumdaki GitHub bağlantı araçlarında desteklenmediğinden Release oluşturulduğu iddia edilmez.  
>
> ---
>
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
