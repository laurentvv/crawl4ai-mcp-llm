# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ [ملف README الإنجليزي](../README.md) هو النسخة المرجعية (متغيرات البيئة، الأمان، التطوير).

أداة قوية للزحف على الويب تتكامل مع مساعدي الذكاء الاصطناعي عبر بروتوكول سياق النموذج (MCP). يتيح هذا المشروع لمساعدي الذكاء الاصطناعي الزحف إلى المواقع الإلكترونية، واستخراج المحتوى الديناميكي، والتنقل عبر الروابط، وحفظ ملفات Markdown المنظمة مباشرة.

## 📋 المميزات

- تكامل أصلي مع مساعدي الذكاء الاصطناعي عبر MCP (`crawl`, `crawl_page`, `close_session`, `open_crawl_explorer`, `view_crawl_file`)
- إرجاع محتوى Markdown المستخرج مباشرة إلى الذكاء الاصطناعي وإتاحة النتائج المحفوظة كموارد MCP (`crawl://results/...`)
- استخراج وعرض الروابط الداخلية/الخارجية للتنقل عبر الذكاء الاصطناعي
- الزحف على المواقع الإلكترونية بعمق وحد صفحات قابل للتهيئة، مع إشعارات تقدم مباشرة وإحصائيات مفصلة
- **تطبيقات MCP التفاعلية (Antigravity / SEP-1865)** — مدمجة مسبقًا داخل حزمة wheel (دون الحاجة إلى Node.js):
  - **بطاقات مدمجة** على `crawl` و `crawl_page` (الحالة، العدادات، معاينة Markdown، تصفية الروابط، والصفحات المتخطاة)
  - **Crawl4AI Explorer** (`open_crawl_explorer`، لوحة جانبية وعرض كامل): تصفح النتائج المحفوظة بترقيم الصفحات، بحث بالاسم/الرابط و**بحث نصي كامل**، **فهرس لكل صفحة** (نسخ أو إرفاق صفحة واحدة فقط)، مشغل زحف وإدارة الجلسات
  - **عارض ملفات مخصص** (`view_crawl_file` لملفات `.crawlmd` / `.crawl.md`): فهرس للصفحات، بيانات وصفية وإعادة زحف بنقرة واحدة
  - توافق نصي كامل بنسبة 100% لعملاء MCP بدون واجهة رسومية

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="تطبيقات Crawl4AI MCP في Antigravity: بطاقة مدمجة ولوحة Crawl4AI Explorer" width="900"/>
</div>

- معالجة الأخطاء وصفحات "غير موجود"
- **قدرات كشط متقدمة**:
  - **تصفية الروابط بأنماط glob**: استهدف أو استبعد المسارات باستخدام `include_patterns` و `exclude_patterns`
  - **الوضع السحري (Magic Mode)**: استدلالات crawl4ai لمحاكاة متصفح حقيقي والمساعدة مع بعض حمايات الروبوتات
  - **استخراج موجه (Targeted Extraction)**: جلب ما تحتاجه فقط باستخدام محددات CSS
  - **جافا سكريبت مخصص** (اختياري): تنفيذ الأكواد قبل الاستخراج (`CRAWL4AI_MCP_ALLOW_JS=true`)
  - **جلسات مستمرة**: متصفح مشترك يحتفظ بملفات تعريف الارتباط والحالة عبر الطلبات (`session_id`)
  - **دعم تطبيقات الصفحة الواحدة (SPA)**: انتظار محددات CSS الديناميكية أو تعيين تأخيرات صريحة قبل الاستخراج

## 🚀 تهيئة MCP

الطريقة الأبسط والموصى بها لاستخدام هذه الأداة هي عبر `uvx`. تضمن اللاحقة `@latest` تشغيل أحدث إصدار منشور من PyPI.

### المتطلبات الأساسية

- تثبيت [uv](https://github.com/astral-sh/uv) على نظامك.

### الإعداد لمساعدي الذكاء الاصطناعي (Claude Desktop و Cline و Antigravity)

أضف ما يلي إلى ملف تهيئة MCP الخاص بمساعد الذكاء الاصطناعي (`cline_mcp_settings.json` أو `claude_desktop_config.json` أو `mcp_config.json`):

> **ملاحظة**: يتطلب Python 3.12 أو 3.13. يوصى بشدة بتحديد `--python 3.13` خصوصًا على نظام ويندوز.

```json
{
  "mcpServers": {
    "crawl": {
      "command": "uvx",
      "args": [
        "--python",
        "3.13",
        "crawl4ai-mcp-llm@latest"
      ],
      "disabled": false,
      "autoApprove": [],
      "timeout": 600
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add crawl -s user -- uvx --python 3.13 crawl4ai-mcp-llm@latest
```

**Google Antigravity (إضافة مع MCP Apps):**

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

### هام: تثبيت المتصفح

يستخدم الزاحف Playwright للتعامل مع المحتوى الديناميكي. ثبّت Chromium مرة واحدة بعد إعداد الأداة:

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## 🖥️ الاستخدام

بمجرد التهيئة، يمكنك استخدام الزاحف من خلال مطالبة مساعد الذكاء الاصطناعي الخاص بك بإجراء عملية زحف.

### أمثلة على الاستخدام

- **صفحة واحدة**: "اقرأ https://docs.python.org/3/library/re.html (هذه الصفحة فقط) ولخّصها."
- **زحف بسيط**: "هل يمكنك الزحف إلى موقع example.com وإعطائي ملخصًا؟"
- **زحف مع خيارات**: "هل يمكنك الزحف إلى https://example.com بعمق 3 وتضمين الروابط الخارجية؟"
- **تصفية الروابط**: "قم بالزحف إلى https://example.com باستخدام `include_patterns=['/docs/*']` و `exclude_patterns=['/docs/legacy/*', '*.pdf']`."
- **المحتوى الديناميكي**: "قم بالزحف إلى تطبيق React هذا وانتظر تحميل محدد `.main-content`."
- **استخراج موجه**: "قم بالزحف إلى موقع التوثيق ولكن استخرج فقط المحتوى المطابق لمحدد `h1, p.lead` CSS."
- **المستكشف التفاعلي (Antigravity)**: "افتح Crawl4AI Explorer للبحث في نتائج الزحف المحفوظة."

## 🛠️ المعلمات المتاحة (أداة `crawl`)

تقبل أداة `crawl` المعلمات التالية:

| المعلمة | النوع | الوصف | القيمة الافتراضية |
|-----------|------|-------------|---------------|
| `url` | string | رابط http(s) للزحف إليه (مطلوب) | - |
| `max_depth` | integer | عمق الروابط المتبعة (0-5): 0 = صفحة البداية فقط، 1 = روابطها، وهكذا | 2 |
| `max_pages` | integer | الحد الأقصى لعدد الصفحات المراد زحفها (1-500) | 50 |
| `include_external` | boolean | تضمين الروابط الخارجية | false |
| `wait_for_selector` | string | محدد CSS للانتظار قبل استخراج المحتوى (مفيد لتطبيقات SPA) | None |
| `return_content` | boolean | ما إذا كان سيتم إرجاع المحتوى المستخرج مباشرة في استجابة MCP | true |
| `max_content_chars` | integer | الحد الأقصى لعدد أحرف المحتوى المُعاد في الاستجابة (1,000-500,000) | 50000 |
| `output_file` | string | اسم ملف Markdown، يُحفظ دائمًا داخل مجلد النتائج | يتم إنشاؤه تلقائيًا |
| `overwrite` | boolean | السماح باستبدال `output_file` موجود | false |
| `magic` | boolean | تفعيل الوضع السحري لـ crawl4ai (استدلالات ضد الروبوتات) | false |
| `css_selector` | string | محدد CSS لاستخراج العناصر المستهدفة فقط من الصفحة | None |
| `js_code` | string | كود جافا سكريبت مخصص قبل الاستخراج (`CRAWL4AI_MCP_ALLOW_JS=true`) | None |
| `session_id` | string | معرف جلسة مستمر للاحتفاظ بملفات تعريف الارتباط وحالة المتصفح | None |
| `delay_before_return_html` | number | تأخير بالثواني (0-60) قبل استخراج HTML (صفحات JS الثقيلة) | None |
| `include_patterns` | array of strings | اتباع الروابط المطابقة لنمط glob واحد على الأقل فقط (مثل `["/docs/*", "*/api/*"]`) | None |
| `exclude_patterns` | array of strings | تخطي الروابط المطابقة لأي نمط glob (مثل `["/blog/*", "*.pdf"]`)؛ له الأولوية على `include_patterns` | None |

## 📄 الترخيص

هذا المشروع مرخص بموجب رخصة MIT.

---

> 🏠 **الكود المصدري والتوثيق**: [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
