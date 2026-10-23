# PROJECT OMEGA — BAŞ MÜFETTİŞ

## Master Engineering Specification — Version 2.0

**Proje türü:** Local-first, güvenli, çok ajanlı yapay zekâ orkestrasyon platformu
**Ana dil:** Türkçe
**Kod ve API standartları:** İngilizce
**Temel amaç:** Kişisel dijital varlık envanteri, güvenli bilgi erişimi, yerel LLM, GitHub Copilot denetimi, çok ajanlı görev yürütme, merkezi yönetim paneli ve izlenebilir otomasyon.

### Vazgeçilmez mimari ilkeler

1. Local-first ve privacy-by-default.
2. Least privilege ve zero-trust yaklaşımı.
3. Secret değerleri asla LLM bağlamına, Git geçmişine veya RAG indeksine girmez.
4. Varsayılan mod read-only ve dry-run olur.
5. Yıkıcı veya dış dünyayı etkileyen işlemler açık insan onayı gerektirir.
6. Her değişiklik loglanır, test edilir, gerektiğinde geri alınır.
7. Tek model, tek GPU, tek bulut veya tek sağlayıcıya bağımlılık oluşturulmaz.
8. Sistem testlerle doğrulanmadan üretime alınmaz.
9. Modelin kararı güvenlik yetkisi olarak kabul edilmez.
10. Bilinmeyen donanım, erişim hakkı, bütçe veya servis varmış gibi davranılmaz.

---

## FAZ 0 — PROJE KEŞFİ VE TEMEL YÖNETİŞİM
**Hedef:** Kod üretiminden önce uygulanabilir ve sınırları belirlenmiş bir sistem tasarlamak.

1. GitHub deposunu incele. Mevcut kod, yapılandırma, test, lisans ve dokümanların envanterini çıkar.
2. İşletim sistemi, CPU, RAM, GPU, VRAM, disk, ağ ve mevcut çalışma ortamını salt okunur komutlarla tespit et.
3. Mevcut repo ve kullanıcı yetkilerini, kapsam dışı sistemleri ve izin verilmiş entegrasyonları belgeleyen scope.yaml oluştur.
4. Gereksinimleri P0 (zorunlu), P1 (önemli) ve P2 (ileri seviye) olarak sınıflandır.
5. Mimari karar kayıtları (ADR) oluştur. Her önemli teknolojinin alternatiflerini ve seçilme nedenini açıkla.
6. Threat modeling yap: veri sızıntısı, prompt injection, supply-chain saldırıları, yetki yükseltme ve kötü amaçlı PR senaryolarını değerlendir.
7. Veri sınıflandırması oluştur: public, internal, confidential, restricted.
8. RTO/RPO, maliyet sınırları, erişilebilirlik ve performans hedeflerini belgele; bilinmeyen hedefler için varsayımlar yerine yapılandırılabilir değerler kullan.
9. Docker Compose tabanlı yerel geliştirme ortamı, .env.example, Makefile ve temel servis health-check'leri oluştur.
10. Mimari diyagram, bağımlılık grafiği, kilometre taşları ve ilk uygulama backlog'unu üret.

**Kabul koşulu:** Proje boş veya örnek verilerle kurulabilir; mimari, izinler ve kapsam açıkça dokümante edilmiştir.

---

## FAZ I — DİJİTAL ENVANTER VE GÜVENLİ VERİ KEŞFİ
**Hedef:** Dağınık dijital varlıkları değiştirmeden keşfetmek.

11. GitHub API ve gh kullanarak yalnızca yetki verilmiş repoları, fork'ları, dalları ve temel metaverileri listele; sayfalama ve API limitlerini destekle.
12. Kullanıcı onayı bulunan Google Cloud hesaplarında proje ve kaynak envanterini çıkar; yeni servis hesabı anahtarı üretme.
13. Google Drive erişimi varsa yalnızca izin verilen klasörlerin dosya metaverilerini indeksle; dosyaları varsayılan olarak indirme.
14. Yerel klasörleri ve takılı diskleri salt okunur modda tara; fiziksel disk imajlamasını ayrı, onay gerektiren adli kopyalama prosedürü olarak ele al.
15. Python, JavaScript, TypeScript, C++, Shell ve yapılandırma dosyalarını otomatik olarak sınıflandır.
16. Gitleaks ve TruffleHog ile izin verilen içerik üzerinde sır taraması yap; bulunan gizli değerleri raporlarda maskele.
17. Bulgular için sağlayıcı türü, kaynak konumu, risk seviyesi ve düzeltme durumunu tut; gerçek token değerlerini envantere yazma.
18. Yetkisiz veya açıklanmış anahtarları ilgili sağlayıcının resmi mekanizmalarıyla iptal etme ve döndürme sürecini tasarla; doğrulama amacıyla keyfi API çağrısı yapma.
19. Dosya metaverileri ve içeriklerin uygun SHA-256 checksum'larını üret; değişiklikleri saptayan sürümlü indeks oluştur.
20. Toplanan verilerin kaynak, sahiplik, erişim seviyesi, son doğrulama ve saklama süresi bilgilerini provenance tablosuna kaydet.

**Kabul koşulu:** Envanter sorgulanabilir; sır değerleri kaydedilmez; sistem kullanıcı verisini değiştirmeden keşif yapabilir.

---

## FAZ II — GÜVENLİ KASA VE KİMLİK YÖNETİMİ
**Hedef:** Sırları merkezileştirilmiş bir açık dosyada tutmak yerine güvenli erişim aracısı oluşturmak.

21. Sır yönetimi için uygun bir çözüm seç: Vault/OpenBao, işletim sistemi secret store veya uygun yönetilen servis. Seçimi threat model'e göre yap.
22. Secret referansları ile secret değerlerini kesin biçimde ayır. Uygulama veritabanında yalnızca referans ve izin verilen metaveriler tutulur.
23. Hizmetler ve ajanlar için ayrı servis kimlikleri oluştur; her birine minimum kapsamlı yetki ver.
24. Kısa ömürlü token ve desteklenen sağlayıcılarda otomatik credential rotation mekanizmalarını yapılandır.
25. Sır kullanımında audit log oluştur; loglara token, parola, özel anahtar veya hassas içerik yazılmasını engelle.
26. Secret redaction, çıktı maskeleme ve hassas veri sızıntısı testlerini CI pipeline'ına ekle.
27. Desteklenen entegrasyonlarda OIDC veya güvenli yetki devri kullan; mümkün olduğunca uzun ömürlü sabit anahtar kullanımından kaçın.
28. Google Drive kullanılırsa yalnızca istemci tarafında şifrelenmiş uygun yedekleri sakla; şifreleme anahtarlarını yedeklerden bağımsız koru.
29. Backup/restore, anahtar kurtarma ve yedeklerin bütünlük doğrulama süreçlerini oluştur.
30. Yetki iptali, cihaz kaybı ve şüpheli erişim için olay müdahale prosedürlerini test et.

**Kabul koşulu:** Ajan hiçbir zaman sınırsız bir secret kataloğunu okuyamaz. Sırlar yalnızca izinli kullanım sırasında uygun çalışma ortamına verilir.

---

## FAZ III — BİLGİ KATMANI VE UZUN SÜRELİ HAFIZA
**Hedef:** Projeleri ve geçmiş çalışmaları anlayabilen, kaynak gösterebilen bir bilgi motoru geliştirmek.

31. Kod, doküman, görev, sohbet, servis ve kullanıcı tercihi için sürümlü veri şemaları oluştur.
32. Python, TypeScript, JavaScript ve desteklenen diğer dilleri Tree-sitter veya uygun ayrıştırıcılarla analiz et.
33. Dosya, sınıf, fonksiyon, import ve çağrı ilişkilerini çıkar; dinamik çağrıların kesin çözümlenemeyebileceğini işaretle.
34. PDF, Markdown, JSON, TXT ve izin verilmiş sohbet dışa aktarımlarını güvenli biçimde dönüştür.
35. İçerikleri gizlilik düzeyi, kaynak ve erişim izinlerine göre filtrele; hassas bilgileri indeksleme öncesinde temizle.
36. PostgreSQL'de canonical metadata, Qdrant'ta vektör indeksleri ve gerektiğinde graph ilişkileri oluştur.
37. Tam metin/BM25 araması ile embedding tabanlı semantik aramayı birleştiren hybrid retrieval uygula.
38. Kod, belge ve görev araması için uygun embedding ve reranking modellerini benchmark sonuçlarına göre seç.
39. Kaynak bağlantısı, sürüm, güncellik, erişim kontrolü ve kullanıcı tarafından silme/unutma işlemlerini destekle.
40. Incremental indexing ve değişiklik izleme servisi kur; ilk sürümde kontrollü tarama kullan, daha sonra webhook ve watcher ekle.

**Kabul koşulu:** Kullanıcı bir kodun nerede bulunduğunu, ne yaptığını ve hangi servislerle ilişkili olduğunu kaynaklarıyla görebilir. İzin verilmeyen içerikler arama sonuçlarına veya LLM bağlamına girmez.

---

## FAZ IV — YEREL YAPAY ZEKÂ VE MODEL ROUTER
**Hedef:** Yerel çalışabilen, mevcut donanıma uyumlu ve modelden bağımsız bir çıkarım katmanı kurmak.

41. Donanımı ölç ve desteklenen çalışma profillerini belirle: CPU-only, single-GPU ve multi-GPU.
42. Başlangıç için Ollama veya llama.cpp gibi uygun bir yerel çalışma motoru seç; ihtiyaç halinde vLLM/SGLang kullanımını benchmark ile değerlendir.
43. Kodlama, genel asistanlık, analiz ve embedding için ayrı model profil tanımları oluştur.
44. Açık ağırlıklı modelleri güncel lisans, Türkçe performansı, araç kullanımı, VRAM ve benchmark sonuçlarına göre seç.
45. Model dosyalarının checksum, lisans, kaynak ve sürüm bilgilerini doğrula.
46. OpenAI uyumlu iç API adaptörü geliştir; kimlik doğrulama, ağ sınırlandırma ve yetkilendirme katmanını ayrı ele al.
47. Model router oluştur: görev türü, gizlilik, gecikme, bütçe, bağlam kapasitesi ve kalite kriterleriyle yönlendirme yap.
48. Model çağrıları için timeout, concurrency limit, token budget, cancellation ve kontrollü retry ekle.
49. Türkçe/İngilizce değerlendirme setleriyle doğruluk, görev başarısı, token/s, TTFT, VRAM ve maliyet ölçümlerini gerçekleştir.
50. Model değişimi, çökme veya kaynak yetersizliği durumları için açık hata raporlama ve yapılandırılabilir fallback mekanizması uygula.

**Kabul koşulu:** Sistemin en az bir desteklenen profilde, gerçek donanım sınırları içinde yerel çıkarım yapabildiği doğrulanır.

---

## FAZ V — BAŞ MÜFETTİŞ ORKESTRASYON ÇEKİRDEĞİ
**Hedef:** Modeli doğrudan sınırsız yetkili yapmak yerine test edilebilir bir kontrol düzlemi kurmak.

51. FastAPI tabanlı orchestrator API ve sürümlü görev şeması geliştir.
52. Görev durum makinesi kur: CREATED, PLANNED, APPROVAL_PENDING, RUNNING, VERIFYING, SUCCEEDED, FAILED, CANCELLED.
53. Her göreve benzersiz ID, owner, budget, izinler, deadline ve trace ID ata.
54. Planner, Executor, Reviewer, Security Auditor ve Memory Curator rollerini ayrı arayüzlerle tanımla.
55. MCP istemci adaptörü ve izin verilen MCP sunucuları için tool registry oluştur; her araca ayrı güven sınırı uygula.
56. Policy engine kur; araç erişimini kullanıcı kimliği, görev amacı, kaynak kapsamı ve işlem riskine göre değerlendir.
57. Sadece okuma, düşük riskli yazma ve yüksek riskli işlem sınıfları tanımla; riskli işlemler için varsayılan deny uygula.
58. Tüm harici araç çıktılarının güvenilmeyen veri olduğunu varsay; prompt injection dayanıklılığı ve veri çıkış kontrolü ekle.
59. Döngüsel görevlerde maksimum adım sayısı, bütçe, başarısızlık sayısı ve durdurma mekanizmalarını uygula.
60. Çalışma geçmişi, ajan kararları, araç sonuçlarının güvenli özetleri ve denetim olaylarını izlenebilir şekilde kaydet.

**Kabul koşulu:** Bir görev planlanır, yetki kontrolünden geçer, izole ortamda yürütülür, değerlendirilir ve nihai durumuyla raporlanır.

---

## FAZ VI — GITHUB COPILOT VE KOD DENETİMİ
**Hedef:** Copilot'un yaptığı değişikliklere bağımsız doğrulama uygulamak.

61. .github/copilot-instructions.md, kök AGENTS.md ve gerekli path-specific talimatları oluştur.
62. Repo için kodlama standartlarını, izinli araçları, test zorunluluklarını ve güvenlik sınırlarını tanımla.
63. Copilot'un desteklenen ajan ve MCP mekanizmalarıyla görev almasını sağla; desteklenmeyen kontrol özelliklerini varmış gibi gösterme.
64. Her kodlama görevi için issue, ayrı branch ve pull request tabanlı iş akışı uygula.
65. Lint, formatting, type-check, unit test, integration test, dependency scanning ve secret scanning CI adımlarını oluştur.
66. Baş Müfettiş için bağımsız PR inceleme servisi geliştir; diff, test sonuçları, risk ve politika uyumunu değerlendir.
67. Denetim servisine ayrı, minimum yetkili GitHub App kimliği tanımla; güvenilir kaynaktan commit SHA'ya bağlı check sonucu yayınla.
68. GitHub Rulesets/branch protection ile gerekli kontroller geçmeden PR birleştirmeyi engelle. Desteklenen plan ve izinleri doğrula.
69. Yüksek riskli değişiklikler için yetkili insan review'u zorunlu tut; yalnızca ajan onayını yeterli sayma.
70. Hatalı PR, başarısız deployment ve geri alma senaryolarını test et; denetim servisi kapalıyken sistemin fail-closed davrandığını doğrula.

**Kabul koşulu:** Uygun yetkilerle kurulan korumalı depoda, kontrol başarısızsa PR birleştirilemez. Ajanın kendi çıktısına verdiği onay güvenlik kontrolünün yerine geçmez.

---

## FAZ VII — WEB YÖNETİM PANELİ
**Hedef:** Sistemin kullanıcı tarafından anlaşılabilir, yönetilebilir ve kontrol edilebilir hale gelmesi.

71. Next.js veya benzeri bir web arayüzü geliştir; arka uçtan net şekilde ayır.
72. Dashboard'da sistem sağlığı, model durumu, görev kuyruğu, maliyet ve kritik uyarıları göster.
73. Dijital envanter ekranında repo, klasör, servis ve veri kaynaklarını filtrelenebilir biçimde göster.
74. Bilgi arama ekranında semantik arama, kaynak doğrulama ve erişim sınıflandırması sun.
75. Ajan görev ekranında plan, adımlar, çalışma durumu, sonuçlar ve durdurma kontrollerini göster.
76. Onay ekranında bekleyen işlemler için hedef kaynak, diff, risk, kapsam, süre ve geri alma bilgisi sun.
77. Secret yönetimi ekranında yalnızca referansları, kullanım izinlerini ve rotasyon durumlarını göster.
78. GitHub PR denetim ekranında test sonuçları, güvenlik bulguları, politika kararları ve review geçmişini göster.
79. Kullanıcı kimlik doğrulama, oturum güvenliği, rol bazlı erişim ve gerektiğinde MFA entegrasyonu ekle.
80. Türkçe varsayılan dil, İngilizce seçeneği, erişilebilirlik, mobil uyumlu web arayüzü ve temel karanlık tema desteği oluştur.

**Kabul koşulu:** Kullanıcı terminale ihtiyaç duymadan görev başlatabilir, izinleri kontrol edebilir, işlemleri onaylayabilir veya durdurabilir; tüm bu eylemler yetkilendirilir.

---

## FAZ VIII — GÜVENLİ OTONOMİ VE KALİTE DEĞERLENDİRMESİ
**Hedef:** Sistemin kendi çıktılarını değerlendirebilmesi, ancak kontrolsüz biçimde değişmemesi.

81. İzole yürütme ortamında işlem türüne uygun container veya microVM güvenlik profilleri oluştur.
82. Varsayılan olarak kapalı ağ erişimi, salt okunur dosya sistemi ve açıkça izin verilen çalışma dizinleri uygula.
83. Sandbox için CPU, RAM, disk, ağ, süre ve process sınırları tanımla.
84. Kod geliştirme döngüsü oluştur: planla, uygula, test et, değerlendir, sınırlı yeniden dene ve raporla.
85. Otomatik düzeltme denemelerini maksimum tekrar ve zaman bütçesiyle sınırlandır.
86. Birim, entegrasyon, regresyon, güvenlik ve uçtan uca test setleri oluştur.
87. Prompt injection, kötü amaçlı dependency, secret exfiltration ve tehlikeli shell komutu senaryolarını adversarial testlere dahil et.
88. Yeni model, prompt veya ajan sürümünü sabit benchmark seti ve önceki sürümle karşılaştır.
89. Hafıza kayıtlarını doğrulanmamış öneri, onaylı bilgi ve test edilmiş çözüm olarak sınıflandır; eğitim verisini ayrı onay sürecinden geçir.
90. Performans düşüşü veya güvenlik regresyonu halinde rollback ve sürüm dondurma mekanizması kur.

**Kabul koşulu:** Sistem hatadan öğrenme amacıyla bilgi kaydedebilir; fakat üretim modeli, izinler veya sistem politikalarını kendi başına değiştiremez.

---

## FAZ IX — ÜRETİM, GÖZLEMLENEBİLİRLİK VE OPERASYON
**Hedef:** Projenin yalnızca demo olarak değil, sürdürülebilir bir sistem olarak çalışması.

91. Prometheus uyumlu metrikler, OpenTelemetry izleri ve güvenli yapılandırılmış loglar oluştur.
92. Grafana panellerinde hata, gecikme, kuyruk, model performansı ve kaynak kullanımı göster.
93. Veri tabanı migration, yedekleme, restore ve sürüm geri alma süreçlerini otomatik test et.
94. SBOM, dependency pinning, image scanning ve yazılım tedarik zinciri kontrollerini uygula.
95. Development, staging ve production ortamlarını ayrı yapılandır; üretim erişimini minimum yetkiyle sınırlandır.
96. HTTPS/TLS, kimlik doğrulama, firewall, VPN ve açık port envanteri kurallarını uygula.
97. Kritik operasyonlar için kill switch, olay müdahalesi, güvenlik uyarıları ve acil erişim iptali oluştur.
98. Sistemi yük, kesinti, GPU yetersizliği, veritabanı arızası ve ağ kaybı senaryolarında test et.
99. Kullanıcı kılavuzu, işletim kılavuzu, API dokümantasyonu, kurulum ve kurtarma prosedürlerini tamamla.
100. Son kabul testlerini gerçek yapılandırılmış ortamda çalıştır; ölçüm, başarısız test, kalan risk ve üretime hazır olma durumunu belgeleyerek sürüm adayı oluştur.

**Kabul koşulu:** Testler, izinler, yedek kurtarma ve güvenlik kontrolleri geçmeden sistem production-ready olarak işaretlenemez.

---

## İLK TESLİM — MINIMUM VIABLE INSPECTOR (MVI)

İlk sürüm, bütün 100 adımı aynı anda gerçekleştirmeye çalışmamalıdır.

İlk teslim kapsamı:
- Docker Compose ile çalışan yerel ortam.
- FastAPI backend.
- PostgreSQL veri katmanı.
- Tek model çalıştırabilen yerel LLM adaptörü.
- Basit görev kuyruğu ve task state machine.
- Salt okunur GitHub repo envanteri.
- Temel secret tarama ve redaction.
- Basit RAG ve kaynak gösterimi.
- GitHub PR inceleme raporu.
- Güvenlik politikası ve kullanıcı onay mekanizması.
- Türkçe web yönetim paneli.
- CI testleri ve kurulum dokümanı.

Bu çekirdek doğrulanmadan ileri model eğitimi, çoklu GPU, otomatik kod birleştirme veya gerçek sistemlerde geniş kapsamlı yazma işlemlerine geçilmemelidir.

## Nihai başarı tanımı

PROJECT OMEGA, ancak aşağıdaki özellikleri gerçek testlerle kanıtlarsa başarılı sayılacaktır:
- Yerel modelle çalışabilir.
- Yetkili dijital varlıkları indeksleyebilir.
- Hassas bilgileri koruyabilir.
- Kullanıcı sorularına kaynak göstererek yanıt verebilir.
- GitHub üzerindeki kod değişikliklerini inceleyebilir.
- Güvenilmeyen ajanları denetim mekanizmasından bağımsız tutabilir.
- Kullanıcı onayı gereken işlemleri durdurabilir.
- Başarısız görevleri ve sebeplerini gösterebilir.
- Yedeklerden geri yüklenebilir.
- Donanım veya entegrasyon sınırlarını dürüstçe raporlayabilir.

**Son kural:** Yapılmayan işi yapılmış gösterme. Test edilmeyen özelliği çalışıyor ilan etme. Yetki verilmeyen kaynağa erişme. Sistem güvenli bir biçimde doğrulanmadığı sürece üretim işlemi gerçekleştirme.
