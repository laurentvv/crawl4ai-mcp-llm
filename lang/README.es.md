# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ El [README en inglés](../README.md) es la versión de referencia (variables de entorno, seguridad, desarrollo).

Una potente herramienta de rastreo web que se integra con asistentes de IA a través de MCP (Model Context Protocol). Este proyecto permite a los asistentes de IA rastrear sitios web, extraer contenido dinámico, navegar por los enlaces y guardar archivos Markdown estructurados directamente.

## 📋 Características

- Integración nativa con asistentes de IA a través de MCP (`crawl`, `crawl_page`, `close_session`, `open_crawl_explorer`, `view_crawl_file`)
- Devuelve el contenido Markdown extraído directamente a la IA y expone los resultados guardados como recursos MCP (`crawl://results/...`)
- Extrae y muestra enlaces internos/externos para la navegación de la IA
- Rastreo de sitios web con profundidad y límite de páginas configurables, notificaciones de progreso en tiempo real y estadísticas detalladas
- **MCP Apps interactivas (Antigravity / SEP-1865)** — preempaquetadas en la wheel (sin Node.js):
  - **Tarjetas inline** en `crawl` y `crawl_page` (estado, métricas, vista previa Markdown renderizada/sin procesar, enlaces filtrables y páginas omitidas)
  - **Crawl4AI Explorer** (`open_crawl_explorer`, panel lateral y pantalla completa): resultados paginados, búsqueda por nombre/URL y **búsqueda de texto completo**, **índice por página** (copiar/adjuntar una sola página), lanzador de rastreo y gestión de sesiones
  - **Visor de archivos personalizado** (`view_crawl_file` para `.crawlmd` / `.crawl.md`): índice por página, metadatos y re-rastreo en un clic
  - 100 % retrocompatible en texto plano para clientes MCP sin interfaz

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="Crawl4AI MCP Apps en Antigravity: tarjeta inline y panel Crawl4AI Explorer" width="900"/>
</div>

- Gestión de errores y páginas no encontradas
- **Capacidades avanzadas de extracción**:
  - **Filtrado de URL con patrones glob**: incluye o excluye rutas con `include_patterns` y `exclude_patterns`
  - **Magic Mode**: heurísticas de crawl4ai que simulan un navegador real y ayudan frente a algunas protecciones anti-bot
  - **Extracción dirigida**: obtén solo lo que necesitas usando selectores CSS
  - **JavaScript personalizado** (opt-in): ejecuta código antes de la extracción (`CRAWL4AI_MCP_ALLOW_JS=true`)
  - **Sesiones persistentes**: un navegador compartido conserva cookies y estado entre llamadas (`session_id`)
  - **Soporte SPA**: espera selectores CSS dinámicos o establece retardos explícitos antes de la extracción

## 🚀 Configuración MCP

La forma más sencilla y recomendada de usar esta herramienta es a través de `uvx`. El sufijo `@latest` asegura que `uvx` ejecute la última versión publicada en PyPI.

### Requisitos previos

- [uv](https://github.com/astral-sh/uv) instalado en tu sistema.

### Configuración para asistentes de IA (Claude Desktop, Cline, Antigravity)

Añade lo siguiente al archivo de configuración MCP de tu asistente de IA (`cline_mcp_settings.json`, `claude_desktop_config.json` o `mcp_config.json`):

> **Nota**: Se requiere Python 3.12 o 3.13. Especificar `--python 3.13` es muy recomendable, especialmente en Windows.

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

**Google Antigravity (plugin con MCP Apps):**

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

### Importante: Instalación del navegador

El rastreador utiliza Playwright para gestionar el contenido dinámico. Instala Chromium una vez después de configurar la herramienta:

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## 🖥️ Uso

Una vez configurado, puedes usar el rastreador pidiendo a tu asistente de IA que realice un rastreo.

### Ejemplos de uso

- **Página única**: "Lee https://docs.python.org/3/library/re.html (solo esa página) y resúmela."
- **Rastreo simple**: "¿Puedes rastrear el sitio example.com y darme un resumen?"
- **Rastreo con opciones**: "¿Puedes rastrear https://example.com con una profundidad de 3 e incluir enlaces externos?"
- **Filtrado de URL**: "Rastrea https://example.com con `include_patterns=['/docs/*']` y `exclude_patterns=['/docs/legacy/*', '*.pdf']`."
- **Contenido dinámico**: "Rastrea esta aplicación React y espera a que se cargue el selector `.main-content`."
- **Extracción dirigida**: "Rastrea el sitio de documentación pero extrae solo el contenido que coincida con el selector CSS `h1, p.lead`."
- **Explorador interactivo (Antigravity)**: "Abre Crawl4AI Explorer para buscar en mis rastreos guardados."

## 🛠️ Parámetros disponibles (herramienta `crawl`)

La herramienta `crawl` acepta los siguientes parámetros:

| Parámetro | Tipo | Descripción | Valor predeterminado |
|-----------|------|-------------|---------------|
| `url` | string | URL http(s) a rastrear (obligatorio) | - |
| `max_depth` | integer | Profundidad de enlaces a seguir (0-5): 0 = solo la página inicial, 1 = sus enlaces, etc. | 2 |
| `max_pages` | integer | Número máximo de páginas a rastrear (1-500) | 50 |
| `include_external` | boolean | Incluir enlaces externos | false |
| `wait_for_selector` | string | Selector CSS a esperar antes de extraer el contenido. Útil para SPA. | None |
| `return_content` | boolean | Si se debe devolver el contenido extraído directamente en la respuesta MCP | true |
| `max_content_chars` | integer | Número máximo de caracteres de contenido devueltos en la respuesta (1 000-500 000) | 50000 |
| `output_file` | string | Nombre del archivo Markdown, siempre guardado en el directorio de resultados | generado automáticamente |
| `overwrite` | boolean | Permitir reemplazar un `output_file` existente | false |
| `magic` | boolean | Activar magic mode de crawl4ai (heurísticas anti-bot) | false |
| `css_selector` | string | Selector CSS específico para extraer solo los elementos dirigidos de la página | None |
| `js_code` | string | Código JavaScript personalizado para ejecutar antes de la extracción (`CRAWL4AI_MCP_ALLOW_JS=true`) | None |
| `session_id` | string | Identificador de sesión persistente para conservar cookies y estado del navegador | None |
| `delay_before_return_html` | number | Retardo en segundos (0-60) antes de extraer el HTML (páginas con mucho JS) | None |
| `include_patterns` | array of strings | Seguir solo URLs que coincidan con al menos un patrón glob (ej. `["/docs/*", "*/api/*"]`) | None |
| `exclude_patterns` | array of strings | Omitir URLs que coincidan con algún patrón glob (ej. `["/blog/*", "*.pdf"]`); prevalece sobre `include_patterns` | None |

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT.

---

> 🏠 **Código fuente y documentación**: [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
