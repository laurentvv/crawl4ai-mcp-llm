# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.jpg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ El [README en inglés](../README.md) es la versión de referencia (variables de entorno, seguridad, desarrollo).

Una potente herramienta de rastreo web que se integra con asistentes de IA a través de MCP (Model Context Protocol). Este proyecto permite a los asistentes de IA rastrear sitios web, extraer contenido dinámico, navegar por los enlaces y guardar archivos Markdown estructurados directamente.

## 📋 Características

- Integración nativa con asistentes de IA a través de MCP
- Devuelve el contenido Markdown extraído directamente a la IA
- Extrae y muestra enlaces internos/externos para la navegación de la IA
- Rastreo de sitios web con profundidad configurable
- Estadísticas detalladas de los resultados del rastreo
- Gestión de errores y páginas no encontradas
- **Capacidades avanzadas de extracción**:
  - **Magic Mode**: Evita los anti-bots (como Cloudflare) y simula el comportamiento real de un navegador
  - **Extracción dirigida**: Obtén solo lo que necesitas usando selectores CSS
  - **JavaScript personalizado**: Ejecuta código antes de la extracción (clics, scrolls, rellenado de formularios)
  - **Sesiones persistentes**: Conserva las cookies y el estado entre solicitudes para sitios autenticados
  - **Soporte SPA**: Espera selectores CSS dinámicos o establece retardos explícitos antes de la extracción

## 🚀 Configuración MCP

La forma más sencilla y recomendada de usar esta herramienta es a través de `uvx`, que obtiene y ejecuta automáticamente la última versión publicada desde PyPI.

### Requisitos previos

- [uv](https://github.com/astral-sh/uv) instalado en tu sistema.

### Configuración para asistentes de IA (por ejemplo, Claude Desktop, Cline)

Añade lo siguiente al archivo de configuración MCP de tu asistente de IA (por ejemplo, `cline_mcp_settings.json` o `claude_desktop_config.json`):

> **Nota para usuarios de Windows**: Es muy recomendable especificar `--python 3.13` para evitar problemas de compilación con ciertas dependencias.

```json
{
  "mcpServers": {
    "crawl": {
      "command": "uvx",
      "args": [
        "--python",
        "3.13",
        "crawl4ai-mcp-llm"
      ],
      "disabled": false,
      "autoApprove": [],
      "timeout": 600
    }
  }
}
```

### Importante: Instalación del navegador

El rastreador utiliza Playwright para gestionar el contenido dinámico. Debes instalar los navegadores necesarios después de configurar la herramienta:

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm playwright install chromium
```

## 🖥️ Uso

Una vez configurado, puedes usar el rastreador pidiendo a tu asistente de IA que realice un rastreo.

### Ejemplos de uso con Claude/Cline

- **Rastreo simple**: "¿Puedes rastrear el sitio example.com y darme un resumen?"
- **Rastreo con opciones**: "¿Puedes rastrear https://example.com con una profundidad de 3 e incluir enlaces externos?"
- **Contenido dinámico**: "Rastrea esta aplicación React y espera a que se cargue el selector `.main-content`."
- **Evitar protecciones**: "Rastrea example.com pero usa 'magic mode' para evadir la protección anti-bot."
- **Extracción dirigida**: "Rastrea el sitio de documentación pero extrae solo el contenido que coincida con el selector CSS `h1, p.lead`."

## 🛠️ Parámetros disponibles (herramienta MCP)

La herramienta `crawl` acepta los siguientes parámetros:

| Parámetro | Tipo | Descripción | Valor predeterminado |
|-----------|------|-------------|---------------|
| `url` | string | URL a rastrear (obligatorio) | - |
| `max_depth` | integer | Profundidad de enlaces a seguir (0-5): 0 = solo la página inicial, 1 = sus enlaces, etc. | 2 |
| `max_pages` | integer | Número máximo de páginas a rastrear (1-500) | 50 |
| `include_external` | boolean | Incluir enlaces externos | false |
| `wait_for_selector` | string | Selector CSS a esperar antes de extraer el contenido. Útil para aplicaciones de página única. | None |
| `return_content` | boolean | Si se debe devolver el contenido extraído directamente en la respuesta MCP (truncado a 50k caracteres si es necesario). | true |
| `max_content_chars` | integer | Número máximo de caracteres de contenido devueltos en la respuesta | 50000 |
| `output_file` | string | Nombre del archivo Markdown, siempre guardado en el directorio de resultados | generado automáticamente |
| `overwrite` | boolean | Permitir reemplazar un `output_file` existente | false |
| `magic` | boolean | Activar magic mode para evadir anti-bots y simular un navegador real | false |
| `css_selector` | string | Selector CSS específico para extraer solo los elementos dirigidos de la página | None |
| `js_code` | string | Código JavaScript personalizado para ejecutar en la página antes de la extracción | None |
| `session_id` | string | Identificador de sesión persistente para conservar cookies y estado del navegador entre solicitudes | None |
| `delay_before_return_html` | number | Retardo en segundos antes de extraer el HTML (útil para páginas con mucho JS) | None |

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT.

---

> 🏠 **Código fuente y documentación**: [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
