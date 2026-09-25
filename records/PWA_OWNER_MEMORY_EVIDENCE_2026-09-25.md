# MEHMET PWA — sahip girişi ve hafıza uygulama kanıtı

Tarih: 2026-09-25.
Uygulama: https://mehmet-pwa-v022-runtime-production.up.railway.app/
Aynı M simgeli MEHMET Yaratılış PWA kullanılıyor. Yeni APK veya paralel ürün oluşturulmadı.

## GUNCEL_DURUM
- PWA kodu: a28485ede67d97e0cc1b12412a28d35a09a1d8f8, runtime-forensic-v022.
- Backend kodu: 55ab515a396980c927a604f72c366211c250d38f, real-ai-backend-p1.
- Runtime dağıtımı: 93ba4908-4f10-4c72-9c50-e4f23598d4ee.
- Backend dağıtımı: d940cf21-e5e1-4304-98cb-ffdfa96b6bc5.
- Sunucu tarafında mevcut HTTP Basic sahip doğrulaması etkinleştirildi. Kalıcı rastgele güçlü parola Railway ortam değişkeninde tutuluyor; burada veya GitHub'da bulunmuyor.
- Canlı /__health: HTTP 200, owner_auth_configured=true, backend_proxy_configured=true.
- Kimlik doğrulanmadan /api/owner/status: HTTP 401 OWNER_AUTH_REQUIRED.
- OWNER durumu artık proxy sunucusunda doğrulanmış girişe göre üretiliyor; telefonun yerel boolean değerinden yetki verilmiyor.
- Model: gpt-5. Sağlayıcının mevcut API anahtarıyla alınan /v1/models listesinde var. Eski gpt-6-astra listede yok ve gerçek çağrıda 403 model_not_found döndürdü.
- SON GERÇEK MODEL ÇAĞRISI: BLOCKED. HTTP 502 dış cevap / sağlayıcı 429 / insufficient_quota. Request ID: a96ce693-da81-4cc2-ba48-55c923bfebf4.
- Başarılı model cevabı alınmadı. Sırf dağıtım SUCCESS diye sohbet PASS sayılmıyor.

## DEVIR_TESLIM
Önce mevcut OpenAI API projesinin kredi/kota/ödeme durumu yetkili hesapta düzeltilmeli. Aynı anahtar korunabilir; hata tek başına yeni API anahtarı gerektiğini kanıtlamaz. Bakiye yükleme veya ödeme işlemi yapılmadı.
Sonra scripts/owner_acceptance.py --live ile gerçek sohbet ve sentetik hafıza-model testi tekrar çalıştırılmalı.
Kullanıcı telefonda /owner-login üzerinden kendi sahip bilgileriyle giriş yapmalı. Bu tur fiziksel telefonda giriş yapılmadı.
Hafıza bölümündeki yeni model paylaşım kutusu varsayılan olarak kapalı. Kullanıcı açınca ve Hafıza etkin ayarı açıkken en son 20 kayıt sınırlı uzunlukta model isteğine eklenir. Aynı sohbetin en son 8 kullanıcı/asistan iletisi de sınırlı bağlam olarak gönderilir.
Telefon uygulaması kapanıp açıldıktan sonra gerçek IndexedDB kaydı ve yeni sohbetten hatırlama ayrıca doğrulanmalı. Depolamayı sil/sıfırla yapılmamalı.

## KANIT_DEFTERI
Yerel gerçek HTTP sunucusu ve test backend'i:
- Kimliksiz istek reddi PASS.
- Yanlış kullanıcı/parola reddi PASS.
- Doğru sahip kimliği ve OWNER durumu PASS.
- Yetkisiz adli rapor/görünüm reddi PASS.
- UTF-8 ve bozuk Basic başlıkları PASS.
- Mock sohbet PASS; gerçek model cevabı değildir.
JavaScript bağlam testleri:
- Hafıza paylaşımı varsayılan kapalı PASS.
- Açık izin ile hafıza bağlama ekleniyor PASS.
- Hafıza kapalıysa modele gönderilmiyor PASS.
- Sohbet oturumları arasında geçmiş izolasyonu PASS.
- İstek bağlamı uzunluk sınırı PASS.
- Yeni JavaScript bağlamı ile sentetik kayıt okuma PASS; gerçek tarayıcı IndexedDB/telefon yeniden açılışı değildir.
Railway ön-dağıtım:
- RUNTIME_SECURITY_SELFTEST=PASS.
- OWNER_AUTH_HTTP_TEST=PASS; NORMAL_USER_NEGATIVE_TEST=PASS.
- OWNER_CHAT_ACCEPTANCE mode=real-provider status=BLOCKED, upstream_code=insufficient_quota.
- Sentetik hafıza-model testi ilk gerçek çağrı kota nedeniyle durduğu için çalışmadı.
Canlı dış erişim:
- /__health HTTP200 ve auth=true.
- Kimliksiz /api/owner/status HTTP401.

## KARAR_KAYITLARI
Orijinal ZIP ve SHA256 korunuyor; yeni app.js/sw.js sürümlü runtime_assets üzerinden uygulanıyor.
Aynı origin, mehmet_pwa_v1 IndexedDB adı ve veritabanı sürümü korunuyor. Telefon verilerine silme/migrasyon uygulanmadı.
Sahip şifresi GitHub, Drive, rapor veya URL'ye yazılmadı.
Model sağlayıcısının anahtarı yalnız backend tarafında kalıyor.
Sağlayıcının ham hata gövdesi ve anahtarı loglanmıyor; izin verilen sınırlı hata kodları kaydediliyor.
Otomatik tekrar eden ücretli model testi bırakılmadı; sonraki normal dağıtımlar yerel/mock güvenlik testlerini çalıştırır.
PR17 model yönlendirmesi birleştirilmedi; mevcut backend üzerinde izinli tek model seçildi.

## HATA_KAYITLARI
Eski model adı: 403 model_not_found; gpt-5 seçimi ile bu hata giderildi.
Mevcut engel: 429 insufficient_quota. Başarısız denemeler PASS olarak kaydedilmedi.
Railway redeploy eski dağıtım kodunu tekrar kullanabiliyor; yeni kaynak için değişken güncellemesinin normal deploy tetiklemesi kullanıldı ve gerçek commit bilgisi kontrol edildi.

## SON_DOGRULANMIS_ANLIK_GORUNTU
OWNER_AUTH=CONFIGURED_AND_SERVER_TESTED
MODEL=gpt-5
REAL_CHAT=BLOCKED_INSUFFICIENT_QUOTA
MEMORY_CONTEXT=IMPLEMENTED_OPT_IN_AND_LOCALLY_TESTED
REAL_MODEL_MEMORY=NOT_VERIFIED
PHONE_LOGIN=NOT_VERIFIED
PHONE_MEMORY_REOPEN=NOT_VERIFIED
TRUSTED_DEVICE_BINDING=NOT_IMPLEMENTED
FULL_OWNER_MAX=NOT_IMPLEMENTED
CROSS_DEVICE_MEMORY_SYNC=NOT_IMPLEMENTED
INTERNET_RESEARCH=NOT_CONFIGURED
THIRD_PARTY_PUBLIC_CHATBOT_OWNER=NOT_CLAIMED

Bu çalışma kişisel MEHMET PWA içindir; dünyadaki başka yapay zekâ ürününün sahibi olunduğuna veya model ağırlıklarına sahipliğe kanıt değildir.
