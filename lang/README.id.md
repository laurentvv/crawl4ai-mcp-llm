# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ [README bahasa Inggris](../README.md) adalah versi acuan (variabel lingkungan, keamanan, pengembangan).

Alat perayapan web (web crawling) canggih yang terintegrasi dengan asisten AI melalui MCP (Model Context Protocol). Proyek ini memungkinkan asisten AI untuk merayapi situs web, mengekstrak konten dinamis, menavigasi melalui tautan, dan menyimpan file Markdown terstruktur secara langsung.

## 📋 Fitur

- Integrasi asli dengan asisten AI melalui MCP (`crawl`, `crawl_page`, `close_session`, `open_crawl_explorer`, `view_crawl_file`)
- Mengembalikan konten Markdown hasil scraping langsung ke AI dan mengekspos hasil tersimpan sebagai resource MCP (`crawl://results/...`)
- Mengekstrak dan menampilkan tautan internal/eksternal untuk navigasi AI
- Perayapan situs web dengan kedalaman dan batas halaman yang dapat dikonfigurasi, notifikasi progres langsung, serta statistik terperinci
- **MCP Apps Interaktif (Antigravity / SEP-1865)** — sudah dibundel di wheel (tanpa Node.js):
  - **Kartu inline** pada `crawl` & `crawl_page` (status, metrik, pratinjau Markdown terender/mentah, tautan yang dapat difilter, halaman dilewati)
  - **Crawl4AI Explorer** (`open_crawl_explorer`, panel samping & layar penuh): daftar hasil berpaginasi, pencarian nama/URL & **pencarian teks penuh**, **daftar isi per halaman** (salin/lampirkan satu halaman), peluncur crawl, dan manajemen sesi
  - **Penampil file khusus** (`view_crawl_file` untuk `.crawlmd` / `.crawl.md`): daftar isi per halaman, metadata, dan re-crawl sekali klik
  - 100% kompatibel mundur dalam teks biasa untuk klien MCP non-UI

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="Crawl4AI MCP Apps di Antigravity: kartu inline dan panel Crawl4AI Explorer" width="900"/>
</div>

- Penanganan kesalahan dan halaman tidak ditemukan
- **Kemampuan Scraping Lanjutan**:
  - **Penyaringan URL Glob**: targetkan atau lewati jalur dengan `include_patterns` dan `exclude_patterns`
  - **Mode Ajaib (Magic Mode)**: heuristik crawl4ai yang mensimulasikan browser nyata dan membantu menghadapi beberapa proteksi anti-bot
  - **Ekstraksi Tertarget**: ambil hanya yang Anda butuhkan menggunakan pemilih CSS
  - **JavaScript Kustom** (opt-in): jalankan kode sebelum ekstraksi (`CRAWL4AI_MCP_ALLOW_JS=true`)
  - **Sesi Persisten**: satu browser bersama menyimpan cookie dan status lintas panggilan (`session_id`)
  - **Dukungan SPA**: tunggu pemilih CSS dinamis atau atur penundaan pra-ekstraksi secara eksplisit

## 🚀 Konfigurasi MCP

Cara termudah dan yang direkomendasikan untuk menggunakan alat ini adalah melalui `uvx`. Akhiran `@latest` memastikan `uvx` selalu menjalankan versi terbaru dari PyPI.

### Prasyarat

- [uv](https://github.com/astral-sh/uv) terinstal di sistem Anda.

### Penyiapan untuk Asisten AI (Claude Desktop, Cline, Antigravity)

Tambahkan berikut ini ke file konfigurasi MCP Asisten AI Anda (`cline_mcp_settings.json`, `claude_desktop_config.json`, atau `mcp_config.json`):

> **Catatan**: Python 3.12 atau 3.13 diperlukan. Menentukan `--python 3.13` sangat disarankan, terutama di Windows.

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

**Google Antigravity (plugin dengan MCP Apps):**

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

### Penting: Instalasi Browser

Perayap menggunakan Playwright untuk menangani konten dinamis. Instal Chromium sekali setelah menyiapkan alat:

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## 🖥️ Penggunaan

Setelah dikonfigurasi, Anda dapat menggunakan perayap dengan meminta asisten AI Anda untuk melakukan perayapan.

### Contoh Penggunaan

- **Satu Halaman**: "Baca https://docs.python.org/3/library/re.html (halaman itu saja) dan ringkas isinya."
- **Perayapan Sederhana**: "Bisakah kamu merayapi situs example.com dan memberi saya ringkasannya?"
- **Perayapan dengan Opsi**: "Bisakah kamu merayapi https://example.com dengan kedalaman 3 dan sertakan tautan eksternal?"
- **Penyaringan URL**: "Rayapi https://example.com dengan `include_patterns=['/docs/*']` dan `exclude_patterns=['/docs/legacy/*', '*.pdf']`."
- **Konten Dinamis**: "Rayapi aplikasi React ini dan tunggu pemilih `.main-content` dimuat."
- **Ekstraksi Tertarget**: "Rayapi situs docs tetapi ekstrak hanya konten yang cocok dengan pemilih CSS `h1, p.lead`."
- **Explorer Interaktif (Antigravity)**: "Buka Crawl4AI Explorer untuk mencari di hasil crawl tersimpan saya."

## 🛠️ Parameter yang Tersedia (Alat `crawl`)

Alat `crawl` menerima parameter berikut:

| Parameter | Tipe | Deskripsi | Nilai Default |
|-----------|------|-------------|---------------|
| `url` | string | URL http(s) untuk dirayapi (diperlukan) | - |
| `max_depth` | integer | Kedalaman tautan yang diikuti (0-5): 0 = hanya halaman awal, 1 = tautan-tautannya, dst. | 2 |
| `max_pages` | integer | Jumlah maksimum halaman yang di-crawl (1-500) | 50 |
| `include_external` | boolean | Sertakan tautan eksternal | false |
| `wait_for_selector` | string | Pemilih CSS untuk ditunggu sebelum mengekstrak konten. Berguna untuk SPA. | None |
| `return_content` | boolean | Apakah akan mengembalikan konten yang diekstrak langsung dalam respons MCP | true |
| `max_content_chars` | integer | Jumlah maksimum karakter konten yang dikembalikan dalam respons (1.000-500.000) | 50000 |
| `output_file` | string | Nama file Markdown, selalu disimpan di direktori hasil | dibuat secara otomatis |
| `overwrite` | boolean | Izinkan menimpa `output_file` yang sudah ada | false |
| `magic` | boolean | Aktifkan mode ajaib crawl4ai (heuristik anti-bot) | false |
| `css_selector` | string | Pemilih CSS spesifik untuk mengekstrak hanya elemen yang ditargetkan dari halaman | None |
| `js_code` | string | Kode JavaScript kustom sebelum ekstraksi (`CRAWL4AI_MCP_ALLOW_JS=true`) | None |
| `session_id` | string | Pengidentifikasi sesi persisten untuk menyimpan cookie dan status browser | None |
| `delay_before_return_html` | number | Penundaan dalam detik (0-60) sebelum mengekstrak HTML (halaman JS berat) | None |
| `include_patterns` | array of strings | Hanya ikuti URL yang cocok dengan minimal satu pola glob (mis. `["/docs/*", "*/api/*"]`) | None |
| `exclude_patterns` | array of strings | Lewati URL yang cocok dengan pola glob (mis. `["/blog/*", "*.pdf"]`); mengalahkan `include_patterns` | None |

## 📄 Lisensi

Proyek ini dilisensikan di bawah Lisensi MIT.

---

> 🏠 **Kode sumber & dokumentasi**: [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
