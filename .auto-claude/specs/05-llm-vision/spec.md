# LLM Vision

## Overview
OpenAI GPT-4 Vision API entegrasyonu. 3 ekran görüntüsünü karşılaştırmalı analiz et.


## Workflow Type
**feature** - Yeni modül geliştirme

## Task Scope
LLM API bağlantısı, prompt yönetimi ve yanıt parsing işlemlerini yapan modül.

### Teknik Detaylar
```python
@dataclass
class AnalysisResult:
    gercek_hareket: bool
    guven_skoru: float          # 0.0-1.0
    degisiklik_aciklamasi: str
    tespit_edilen_nesneler: List[str]
    tehdit_seviyesi: str        # yok|dusuk|orta|yuksek
    onerilen_aksiyon: str
    detayli_analiz: str
    raw_response: dict
    processing_time: float

class LLMAnalyzer:
    def __init__(self, config: LLMConfig)
    async def analyze(self, screenshots: ScreenshotSet) -> AnalysisResult
    async def analyze_with_retry(self, screenshots: ScreenshotSet, max_retries: int = 3) -> AnalysisResult
```

### Türkçe Prompt
```
Sen bir güvenlik kamerası görüntü analiz uzmanısın. Sana 3 görüntü veriyorum:
1. ÖNCE: Hareket algılanmadan 3 saniye önce
2. ŞİMDİ: Hareket algılandığı an
3. SONRA: Hareket algılandıktan 3 saniye sonra

Bu 3 görüntüyü karşılaştırarak analiz et ve JSON formatında yanıt ver.
```

### Konfigürasyon
```yaml
llm:
  provider: "openai"
  model: "gpt-4-vision-preview"
  api_key: "${OPENAI_API_KEY}"
  max_tokens: 1000
  timeout: 30
```

## Requirements
1. openai Python SDK kullanımı
2. 3 görüntüyü base64 olarak gönder
3. Türkçe system prompt
4. JSON response parsing
5. Rate limiting (utils.RateLimiter)
6. Exponential backoff retry

## Files to Modify
- Yok

## Files to Reference
- `src/config.py` - LLMConfig dataclass
- `src/utils.py` - RateLimiter, retry_async
- `src/screenshot_manager.py` - ScreenshotSet
- `.auto-claude/test_data/LLM_PROMPTS.md` - Prompt örnekleri

## Success Criteria
- [ ] OpenAI API bağlantısı çalışıyor
- [ ] 3 görüntü başarıyla gönderiliyor
- [ ] JSON yanıt doğru parse ediliyor
- [ ] Türkçe analiz döndürülüyor
- [ ] Retry mekanizması çalışıyor
- [ ] Rate limiting aktif

## QA Acceptance Criteria
- Unit test: Mock API ile response parsing
- Integration test: Gerçek API ile test senaryoları
- Error handling: Invalid response, timeout, rate limit

## Dependencies
- 01-project-structure
- 04-screenshot-system

## Notes
- API key environment variable'dan okunacak
- Cost tracking opsiyonel olarak eklenebilir
- Response cache düşünülebilir (aynı görüntü)
