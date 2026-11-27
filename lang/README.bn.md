# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ [ইংরেজি README](../README.md) হলো রেফারেন্স সংস্করণ (এনভায়রনমেন্ট ভেরিয়েবল, নিরাপত্তা, ডেভেলপমেন্ট)।

একটি শক্তিশালী ওয়েব ক্রলিং টুল যা MCP (Model Context Protocol)-এর মাধ্যমে AI সহকারীদের সাথে একীভূত হয়। এই প্রকল্পটি AI সহকারীদের ওয়েবসাইট ক্রল করতে, গতিশীল কন্টেন্ট এক্সট্র্যাক্ট করতে, লিঙ্কের মাধ্যমে নেভিগেট করতে এবং সরাসরি কাঠামোগত Markdown ফাইল সংরক্ষণ করতে সক্ষম করে।

## 📋 বৈশিষ্ট্যসমূহ

- MCP-এর মাধ্যমে AI সহকারীদের সাথে নেটিভ একীকরণ (`crawl`, `crawl_page`, `close_session`, `open_crawl_explorer`, `view_crawl_file`)
- স্ক্র্যাপ করা Markdown কন্টেন্ট সরাসরি AI-তে ফেরত দেওয়া এবং সংরক্ষিত ফলাফল MCP রিসোর্স (`crawl://results/...`) হিসেবে প্রদর্শন করা
- AI নেভিগেশনের জন্য অভ্যন্তরীণ/বাহ্যিক লিঙ্ক এক্সট্র্যাক্ট এবং প্রদর্শন করা
- কনফিগারযোগ্য গভীরতা ও পৃষ্ঠা সীমা, লাইভ অগ্রগতি বিজ্ঞপ্তি এবং বিস্তারিত পরিসংখ্যানসহ ওয়েবসাইট ক্রলিং
- **ইন্টারেক্টিভ MCP Apps (Antigravity / SEP-1865)** — wheel-এ প্রি-বান্ডেল করা (Node.js প্রয়োজন নেই):
  - `crawl` এবং `crawl_page`-এর **ইনলাইন কার্ড** (স্ট্যাটাস, পরিসংখ্যান, রেন্ডার্ড/র Markdown প্রিভিউ, ফিল্টারযোগ্য লিঙ্ক, বাদ পড়া পৃষ্ঠা)
  - **Crawl4AI Explorer** (`open_crawl_explorer`, সাইড প্যানেল ও ফুল পেজ): পেজিনেটেড ফলাফল ব্রাউজার, নাম/URL ও **ফুল-টেক্সট সার্চ**, **প্রতি-পৃষ্ঠা TOC** (একটি পৃষ্ঠা কপি/অ্যাটাচ), ক্রল লঞ্চার এবং সেশন ম্যানেজার
  - **কাস্টম ফাইল ভিউয়ার** (`.crawlmd` / `.crawl.md`-এর জন্য `view_crawl_file`): প্রতি-পৃষ্ঠা TOC, মেটাডেটা এবং এক-ক্লিক রি-ক্রল
  - নন-UI MCP ক্লায়েন্টের জন্য ১০০% প্লেইন-টেক্সট সামঞ্জস্য

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="Antigravity-তে Crawl4AI MCP Apps: ইনলাইন কার্ড ও Crawl4AI Explorer সাইড প্যানেল" width="900"/>
</div>

- ত্রুটি এবং পাওয়া যায়নি এমন পৃষ্ঠার হ্যান্ডলিং
- **উন্নত স্ক্র্যাপিং সক্ষমতা**:
  - **URL Glob ফিল্টারিং**: `include_patterns` এবং `exclude_patterns` দিয়ে নির্দিষ্ট পাথ অন্তর্ভুক্ত বা বাদ দিন
  - **ম্যাজিক মোড**: crawl4ai হিউরিস্টিক্স যা বাস্তব ব্রাউজারের আচরণ অনুকরণ করে এবং কিছু অ্যান্টি-বট সুরক্ষায় সাহায্য করে
  - **টার্গেটেড এক্সট্র্যাকশন**: CSS সিলেক্টর ব্যবহার করে শুধুমাত্র প্রয়োজনীয় বিষয়বস্তু আনুন
  - **কাস্টম জাভাস্ক্রিপ্ট** (অপ্ট-ইন): এক্সট্র্যাকশনের আগে কোড চালান (`CRAWL4AI_MCP_ALLOW_JS=true`)
  - **স্থায়ী সেশন**: শেয়ার্ড ব্রাউজার কলের মধ্যে কুকিজ এবং স্টেট বজায় রাখে (`session_id`)
  - **SPA সমর্থন**: গতিশীল CSS সিলেক্টরের জন্য অপেক্ষা করুন অথবা স্পষ্ট প্রি-এক্সট্র্যাকশন বিলম্ব নির্ধারণ করুন

## 🚀 MCP কনফিগারেশন

এই টুল ব্যবহারের সবচেয়ে সহজ এবং প্রস্তাবিত উপায় হলো `uvx`-এর মাধ্যমে। `@latest` যুক্ত করলে `uvx` সর্বদা PyPI থেকে সর্বশেষ প্রকাশিত সংস্করণ চালায়।

### পূর্বশর্ত

- আপনার সিস্টেমে [uv](https://github.com/astral-sh/uv) ইনস্টল থাকতে হবে।

### AI সহকারীদের জন্য সেটআপ (Claude Desktop, Cline, Antigravity)

আপনার AI সহকারীর MCP কনফিগারেশন ফাইলে (`cline_mcp_settings.json`, `claude_desktop_config.json` বা `mcp_config.json`) নিম্নলিখিত অংশ যোগ করুন:

> **নোট**: Python 3.12 বা 3.13 প্রয়োজন। বিশেষত Windows-এ `--python 3.13` নির্দিষ্ট করা অত্যন্ত সুপারিশ করা হয়।

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

**Google Antigravity (MCP Apps প্লাগইন):**

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

### গুরুত্বপূর্ণ: ব্রাউজার ইনস্টলেশন

ক্রলারটি গতিশীল কন্টেন্ট হ্যান্ডল করতে Playwright ব্যবহার করে। সেটআপের পর একবার Chromium ইনস্টল করুন:

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## 🖥️ ব্যবহার

একবার কনফিগার করা হলে, আপনি আপনার AI সহকারীকে একটি ক্রল সম্পাদনের জন্য অনুরোধ করে ক্রলারটি ব্যবহার করতে পারেন।

### ব্যবহারের উদাহরণ

- **একক পৃষ্ঠা**: "https://docs.python.org/3/library/re.html (শুধুমাত্র এই পৃষ্ঠাটি) পড়ুন এবং সারাংশ দিন।"
- **সাধারণ ক্রল**: "আপনি কি example.com সাইটটি ক্রল করে আমাকে একটি সারাংশ দিতে পারেন?"
- **অপশনসহ ক্রল**: "আপনি কি https://example.com কে 3 গভীরতায় ক্রল করতে পারেন এবং বাহ্যিক লিঙ্ক অন্তর্ভুক্ত করতে পারেন?"
- **URL ফিল্টারিং**: "`include_patterns=['/docs/*']` এবং `exclude_patterns=['/docs/legacy/*', '*.pdf']` দিয়ে https://example.com ক্রল করুন।"
- **গতিশীল কন্টেন্ট**: "এই React অ্যাপটি ক্রল করুন এবং `.main-content` সিলেক্টর লোড হওয়া পর্যন্ত অপেক্ষা করুন।"
- **টার্গেটেড এক্সট্র্যাকশন**: "ডক্স সাইটটি ক্রল করুন কিন্তু শুধুমাত্র `h1, p.lead` CSS সিলেক্টরের সাথে মিলে যাওয়া কন্টেন্ট এক্সট্র্যাক্ট করুন।"
- **ইন্টারেক্টিভ এক্সপ্লোরার (Antigravity)**: "আমার সংরক্ষিত ক্রলগুলো খুঁজতে Crawl4AI Explorer খুলুন।"

## 🛠️ উপলব্ধ প্যারামিটার (`crawl` টুল)

`crawl` টুলটি নিম্নলিখিত প্যারামিটারগুলি গ্রহণ করে:

| প্যারামিটার | টাইপ | বিবরণ | ডিফল্ট মান |
|-----------|------|-------------|---------------|
| `url` | string | ক্রল করার জন্য http(s) URL (আবশ্যক) | - |
| `max_depth` | integer | অনুসরণ করার লিঙ্কের গভীরতা (0-5): 0 = শুধুমাত্র শুরুর পৃষ্ঠা, 1 = তার লিঙ্কগুলি, ইত্যাদি | 2 |
| `max_pages` | integer | ক্রল করার সর্বোচ্চ পৃষ্ঠার সংখ্যা (1-500) | 50 |
| `include_external` | boolean | বাহ্যিক লিঙ্ক অন্তর্ভুক্ত করুন | false |
| `wait_for_selector` | string | কন্টেন্ট এক্সট্র্যাক্ট করার আগে অপেক্ষা করার CSS সিলেক্টর (SPA-এর জন্য কার্যকর) | None |
| `return_content` | boolean | এক্সট্র্যাক্ট করা কন্টেন্ট সরাসরি MCP রেসপন্সে ফেরত দেবে কিনা | true |
| `max_content_chars` | integer | প্রতিক্রিয়ায় ফেরত দেওয়া বিষয়বস্তুর সর্বোচ্চ অক্ষর সংখ্যা (1,000-500,000) | 50000 |
| `output_file` | string | Markdown ফাইলের নাম, সর্বদা ফলাফল ডিরেক্টরিতে সংরক্ষিত হয় | স্বয়ংক্রিয়ভাবে তৈরি হয় |
| `overwrite` | boolean | বিদ্যমান `output_file` প্রতিস্থাপনের অনুমতি দিন | false |
| `magic` | boolean | crawl4ai ম্যাজিক মোড সক্ষম করুন (অ্যান্টি-বট হিউরিস্টিক্স) | false |
| `css_selector` | string | পৃষ্ঠা থেকে শুধুমাত্র টার্গেটেড এলিমেন্ট এক্সট্র্যাক্ট করতে CSS সিলেক্টর | None |
| `js_code` | string | এক্সট্র্যাকশনের আগে কাস্টম জাভাস্ক্রিপ্ট কোড (`CRAWL4AI_MCP_ALLOW_JS=true`) | None |
| `session_id` | string | কুকিজ এবং ব্রাউজার স্টেট বজায় রাখতে স্থায়ী সেশন শনাক্তকারী | None |
| `delay_before_return_html` | number | HTML এক্সট্র্যাক্ট করার আগে অপেক্ষার সময় সেকেন্ডে (0-60) | None |
| `include_patterns` | array of strings | কমপক্ষে একটি glob প্যাটার্নের সাথে মেলে এমন URL অনুসরণ করুন (যেমন `["/docs/*", "*/api/*"]`) | None |
| `exclude_patterns` | array of strings | যেকোনো glob প্যাটার্নের সাথে মেলে এমন URL বাদ দিন (যেমন `["/blog/*", "*.pdf"]`); `include_patterns`-এর ওপর অগ্রাধিকার পায় | None |

## 📄 লাইসেন্স

এই প্রকল্পটি MIT লাইসেন্সের অধীনে লাইসেন্সকৃত।

---

> 🏠 **সোর্স কোড ও ডকুমেন্টেশন**: [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
