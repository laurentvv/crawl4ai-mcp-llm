# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ O [README em inglês](../README.md) é a versão de referência (variáveis de ambiente, segurança, desenvolvimento).

Uma poderosa ferramenta de rastreamento web que se integra com assistentes de IA através do MCP (Model Context Protocol). Este projeto permite que assistentes de IA rastreiem sites, extraiam conteúdo dinâmico, naveguem através de links e salvem arquivos Markdown estruturados diretamente.

## 📋 Funcionalidades

- Integração nativa com assistentes de IA via MCP (`crawl`, `crawl_page`, `close_session`, `open_crawl_explorer`, `view_crawl_file`)
- Retorna o conteúdo Markdown extraído diretamente para a IA e expõe os resultados salvos como recursos MCP (`crawl://results/...`)
- Extrai e exibe links internos/externos para navegação da IA
- Rastreamento de sites com profundidade e limite de páginas configuráveis, notificações de progresso ao vivo e estatísticas detalhadas
- **MCP Apps interativos (Antigravity / SEP-1865)** — pré-empacotados na wheel (sem Node.js):
  - **Cartões inline** em `crawl` e `crawl_page` (status, métricas, visualização Markdown renderizada/bruta, links filtráveis e páginas ignoradas)
  - **Crawl4AI Explorer** (`open_crawl_explorer`, painel lateral e tela cheia): resultados paginados, busca por nome/URL e **busca de texto completo**, **índice por página** (copiar/anexar uma única página), lançador de rastreamento e gestão de sessões
  - **Visualizador de arquivos dedicado** (`view_crawl_file` para `.crawlmd` / `.crawl.md`): índice por página, metadados e re-rastreamento em um clique
  - 100% retrocompatível em texto puro para clientes MCP sem interface

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="Crawl4AI MCP Apps no Antigravity: cartão inline e painel Crawl4AI Explorer" width="900"/>
</div>

- Tratamento de erros e páginas não encontradas
- **Capacidades Avançadas de Rastreamento**:
  - **Filtragem de URL com padrões glob**: selecione ou exclua caminhos com `include_patterns` e `exclude_patterns`
  - **Modo Mágico**: heurísticas do crawl4ai que simulam um navegador real e ajudam com algumas proteções anti-bot
  - **Extração Direcionada**: obtenha apenas o que precisa usando seletores CSS
  - **JavaScript Personalizado** (opt-in): execute código antes da extração (`CRAWL4AI_MCP_ALLOW_JS=true`)
  - **Sessões Persistentes**: um navegador compartilhado mantém cookies e estado entre chamadas (`session_id`)
  - **Suporte a SPA**: aguarde seletores CSS dinâmicos ou defina atrasos explícitos antes da extração

## 🚀 Configuração do MCP

A maneira mais simples e recomendada de usar esta ferramenta é via `uvx`. O sufixo `@latest` faz o `uvx` executar a versão mais recente publicada no PyPI.

### Pré-requisitos

- [uv](https://github.com/astral-sh/uv) instalado no seu sistema.

### Configuração para Assistentes de IA (Claude Desktop, Cline, Antigravity)

Adicione o seguinte ao arquivo de configuração MCP do seu assistente de IA (`cline_mcp_settings.json`, `claude_desktop_config.json` ou `mcp_config.json`):

> **Nota**: Python 3.12 ou 3.13 é obrigatório. Especificar `--python 3.13` é altamente recomendável, especialmente no Windows.

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

**Google Antigravity (plugin com MCP Apps):**

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

### Importante: Instalação do Navegador

O rastreador usa Playwright para lidar com conteúdo dinâmico. Instale o Chromium uma vez após configurar a ferramenta:

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## 🖥️ Uso

Uma vez configurado, você pode usar o rastreador pedindo ao seu assistente de IA para realizar um rastreamento.

### Exemplos de Uso

- **Página Única**: "Leia https://docs.python.org/3/library/re.html (apenas essa página) e faça um resumo."
- **Rastreamento Simples**: "Você pode rastrear o site example.com e me dar um resumo?"
- **Rastreamento com Opções**: "Você pode rastrear https://example.com com profundidade 3 e incluir links externos?"
- **Filtragem de URL**: "Rastreie https://example.com com `include_patterns=['/docs/*']` e `exclude_patterns=['/docs/legacy/*', '*.pdf']`."
- **Conteúdo Dinâmico**: "Rastreie este app React e aguarde o seletor `.main-content` carregar."
- **Extração Direcionada**: "Rastreie o site de documentação mas extraia apenas o conteúdo correspondente ao seletor CSS `h1, p.lead`."
- **Explorador Interativo (Antigravity)**: "Abra o Crawl4AI Explorer para pesquisar nos meus rastreamentos salvos."

## 🛠️ Parâmetros Disponíveis (Ferramenta `crawl`)

A ferramenta `crawl` aceita os seguintes parâmetros:

| Parâmetro | Tipo | Descrição | Valor Padrão |
|-----------|------|-------------|--------------|
| `url` | string | URL http(s) para rastrear (obrigatório) | - |
| `max_depth` | integer | Profundidade de links a seguir (0-5): 0 = apenas a página inicial, 1 = seus links, etc. | 2 |
| `max_pages` | integer | Número máximo de páginas a rastrear (1-500) | 50 |
| `include_external` | boolean | Incluir links externos | false |
| `wait_for_selector` | string | Seletor CSS a aguardar antes de extrair o conteúdo. Útil para SPA. | None |
| `return_content` | boolean | Se deve retornar o conteúdo extraído diretamente na resposta MCP | true |
| `max_content_chars` | integer | Número máximo de caracteres de conteúdo retornados na resposta (1.000-500.000) | 50000 |
| `output_file` | string | Nome do arquivo Markdown, sempre salvo no diretório de resultados | gerado automaticamente |
| `overwrite` | boolean | Permitir substituir um `output_file` existente | false |
| `magic` | boolean | Habilitar modo mágico do crawl4ai (heurísticas anti-bot) | false |
| `css_selector` | string | Seletor CSS específico para extrair apenas elementos direcionados da página | None |
| `js_code` | string | Código JavaScript personalizado para executar antes da extração (`CRAWL4AI_MCP_ALLOW_JS=true`) | None |
| `session_id` | string | Identificador de sessão persistente para manter cookies e estado do navegador | None |
| `delay_before_return_html` | number | Atraso em segundos (0-60) antes de extrair o HTML (páginas JS pesadas) | None |
| `include_patterns` | array of strings | Seguir apenas URLs que correspondam a pelo menos um padrão glob (ex. `["/docs/*", "*/api/*"]`) | None |
| `exclude_patterns` | array of strings | Ignorar URLs que correspondam a algum padrão glob (ex. `["/blog/*", "*.pdf"]`); prevalece sobre `include_patterns` | None |

## 📄 Licença

Este projeto está licenciado sob a Licença MIT.

---

> 🏠 **Código-fonte e documentação**: [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
