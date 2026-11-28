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

# 2026-11-28 Müfettiş 9. Tur: Ek hedefler ve kanıt denetimi

Bu ek, mevcut 100 maddenin kapsamını genişletir; 100 maddenin tamamlandığını iddia etmez. Mevcut maddelerin kutuları, her birinin exact-SHA kod/test/ortam kanıtı eşleştirilmeden tamamlandı olarak işaretlenmeyecektir.

## A. Google Play gelir ve payout mutabakatı

- [ ] Mevcut Play Console ödeme profili, birincil banka hesabı, ürün kimlikleri ve abonelik koşullarını değiştirmeden koru.
- [ ] Play Billing satın alma token'larını güvenilir backend üzerinde Google Play Developer API ile doğrula.
- [ ] Play finansal/earnings raporlarını salt okunur biçimde içe aktar.
- [ ] Rapor satırlarını rapor kimliği + satır kimliği ile idempotent kaydet.
- [ ] Ücret, vergi, iade, chargeback ve para birimi dönüşümünü rapor verisine göre ayrı göster.
- [ ] Google tarafından bildirilen payout referansını ayrı kaydet ve dönem/para birimi mutabakatı yap.
- [ ] Banka hesabı, IBAN, kart veya bankacılık kimlik bilgisi saklama.
- [ ] Google Play adına banka transferi başlatan API veya otomasyon yazma.
- [ ] Test lisansı ile satın alma, yenileme, restore, iptal ve refund akışlarını doğrula.
- [ ] Finansal rapor ve banka ekstresi farkı için denetlenebilir mutabakat raporu üret.

## B. OMEGA AI güvenlik çekirdeği

- [ ] Owner kimliğini e-posta/telefon beyanından değil, kayıtlı cihaz anahtarıyla kriptografik doğrula.
- [ ] Principal nesnesini yalnızca güvenilir sunucu kimlik doğrulama katmanının üretmesini sağla.
- [ ] Model çıktısını hiçbir zaman yetki veya onay kaynağı kabul etme.
- [ ] GitHub, Drive ve Play için ayrı, salt okunur ve kapsamı daraltılmış yetenekler tanımla.
- [ ] Bilinmeyen araç, yazma, silme, merge, deploy ve para hareketi eylemlerini varsayılan olarak reddet.
- [ ] Repository, web, doküman ve tool içeriklerini güvenilmeyen veri olarak sınırla.
- [ ] Prompt injection testlerini gerçek tool-call policy katmanında doğrula.
- [ ] Key rotation, revoke, replay koruması ve cihaz kurtarma prosedürünü uygula.
- [ ] Her yetki kararını secret içermeyen audit kaydıyla ilişkilendir.
- [ ] Yetki katmanı ile gerçek GitHub/Drive/Play connector entegrasyonlarını ayrı kabul testlerinden geçir.

## C. 100 madde geçmiş kanıt denetimi

Her madde için ayrı kayıt: madde numarası, main'deki dosya/commit, PR numarası ve merge durumu, exact commit SHA, CI sonucu, gerçek cihaz/deployment kanıtı, sınıflandırma ve eksik kabul testi.

Kanıt sınıfları:
- MAIN_VERIFIED: main üzerinde mevcut kod + ilgili test/CI kanıtı.
- MERGED_NON_MAIN: PR merge edilmiş olsa bile hedef dal main değil.
- CANDIDATE_ONLY: açık veya kapalı fakat merge edilmemiş PR/branch.
- DOC_ONLY: yalnızca tasarım/rapor mevcut.
- PARTIAL: kod var, fakat maddenin tüm kabul ölçütleri geçmemiş.
- NOT_FOUND: incelenen kaynaklarda kanıt bulunamadı.
- UNVERIFIED: erişim veya exact-SHA doğrulaması eksik.

Başlangıçta doğrulanmış referanslar:
- PR #4: depo güvenlik temeli ve CODEOWNERS değişiklikleri, main'e merge edilmiş. Bu, branch protection'ın etkin olduğunu tek başına kanıtlamaz.
- PR #5: yeniden kullanılabilir Python CI, main'e merge edilmiş.
- PR #6: privacy guard, main'e merge edilmiş.
- PR #14: master roadmap ve kontrol belgeleri, main'e merge edilmiş.
- PR #15: P1 backend uçları, rate limit, request ID ve provider allowlist, main'e merge edilmiş.
- PR #38: Phase 0 mimari/scope belgesi, main'e merge edilmiş.
- PR #39: Compose geliştirme kurulumu, main'e merge edilmiş.
- PR #99: P-256 owner-chat çalışması real-ai-backend-p1 dalına merge edilmiş; main'e merge edilmiş sayılmaz.
- PR #106: predeploy diagnostics real-ai-backend-p1 dalına merge edilmiş; main'e merge edilmiş sayılmaz.
- PR #69: 91 uzman dosyasını içeren entegrasyon adayı açık draft; main kabulü değildir.
- PR #108: bu 100 maddelik yol haritasını main'e ekleyen dokümantasyon PR'ı; uygulama kodu veya runtime kabulü değildir.

Bu referanslar tam 100-madde eşlemesi değildir. Her maddenin ayrı exact-SHA incelemesi tamamlanmadan toplam tamamlanma sayısı açıklanmayacaktır.

## D. Demo ve yayın kanıtı

- [ ] Temiz kurulum, açılış, restart ve upgrade akışını gerçek Android cihazda kaydet.
- [ ] Backend health ile gerçek model/provider durumunu ayrı göster.
- [ ] AI sohbeti ve adversarial prompt injection testini kaydet.
- [ ] Play lisans test kullanıcısıyla satın alma/restore/iptal/refund akışını göster.
- [ ] Payout ekranında yalnızca sentetik finansal veri ve mutabakat göster; gerçek banka bilgisi gösterme.
- [ ] Owner proof, yetkisiz kullanıcı reddi, bilinmeyen tool reddi ve write-denial kanıtlarını kaydet.
- [ ] Exact source SHA, workflow run, artifact SHA-256 ve signer fingerprint eşleşmesini göster.
- [ ] Test edilmeyen özellikleri videoda açıkça NOT TESTED olarak belirt.

## Bu turda eklenen aday dosyalar

Bu dosyalar yalnızca aşağıdaki branch'te yer alır; main'e merge edilmemiştir:
- backend/omega_ai/policy.py
- backend/payouts/ledger.py
- tests/test_omega_ai_policy.py
- tests/test_payout_ledger.py
- docs/OMEGA_PAYOUT_AND_PLAY_BILLING.md
- docs/OMEGA_DEMO_SCRIPT.md

Branch: codex/omega-payout-ai-foundation-20261128

Kabul sınırı: Kodun branch'e yazılması, testlerin GitHub Actions'ta geçmesi veya doküman eklenmesi tek başına production kabulü değildir. Gerçek Play hesabı, gerçek Drive/GitHub yetkileri, kriptografik cihaz kaydı, Android cihaz testi ve bağımsız güvenlik incelemesi ayrıca gereklidir.
