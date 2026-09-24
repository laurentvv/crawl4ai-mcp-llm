# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.jpg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ O [README em inglês](../README.md) é a versão de referência (variáveis de ambiente, segurança, desenvolvimento).

Uma poderosa ferramenta de rastreamento web que se integra com assistentes de IA através do MCP (Model Context Protocol). Este projeto permite que assistentes de IA rastreiem sites, extraiam conteúdo dinâmico, naveguem através de links e salvem arquivos Markdown estruturados diretamente.

## 📋 Funcionalidades

- Integração nativa com assistentes de IA via MCP
- Retorna o conteúdo Markdown extraído diretamente para a IA
- Extrai e exibe links internos/externos para navegação da IA
- Rastreamento de sites com profundidade configurável
- Estatísticas detalhadas dos resultados do rastreamento
- Tratamento de erros e páginas não encontradas
- **Capacidades Avançadas de Rastreamento**:
  - **Modo Mágico**: Contorne proteções anti-bot (como Cloudflare) e simule o comportamento de um navegador real
  - **Extração Direcionada**: Obtenha apenas o que você precisa usando seletores CSS
  - **JavaScript Personalizado**: Execute código antes da extração (cliques, rolagens, preenchimento de formulários)
  - **Sessões Persistentes**: Mantenha cookies e estado entre solicitações para sites autenticados
  - **Suporte a SPA**: Aguarde por seletores CSS dinâmicos ou defina atrasos explícitos antes da extração

## 🚀 Configuração do MCP

A maneira mais simples e recomendada de usar esta ferramenta é via `uvx`, que baixa e executa automaticamente a versão mais recente publicada no PyPI.

### Pré-requisitos

- [uv](https://github.com/astral-sh/uv) instalado no seu sistema.

### Configuração para Assistentes de IA (ex: Claude Desktop, Cline)

Adicione o seguinte ao arquivo de configuração MCP do seu assistente de IA (ex: `cline_mcp_settings.json` ou `claude_desktop_config.json`):

> **Nota para usuários Windows**: É altamente recomendável especificar `--python 3.13` para evitar problemas de compilação com certas dependências.

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

### Importante: Instalação do Navegador

O rastreador usa Playwright para lidar com conteúdo dinâmico. Você deve instalar os navegadores necessários após configurar a ferramenta:

```bash
uvx --from crawl4ai-mcp-llm playwright install chromium
```

## 🖥️ Uso

Uma vez configurado, você pode usar o rastreador pedindo ao seu assistente de IA para realizar um rastreamento.

### Exemplos de Uso com Claude/Cline

- **Rastreamento Simples**: "Você pode rastrear o site example.com e me dar um resumo?"
- **Rastreamento com Opções**: "Você pode rastrear https://example.com com uma profundidade de 3 e incluir links externos?"
- **Conteúdo Dinâmico**: "Rastreie este app React e aguarde o seletor `.main-content` carregar."
- **Contornar Proteções**: "Rastreie example.com mas use o 'modo mágico' para contornar a proteção anti-bot."
- **Extração Direcionada**: "Rastreie o site de documentação mas extraia apenas o conteúdo correspondente ao seletor CSS `h1, p.lead`."

## 🛠️ Parâmetros Disponíveis (Ferramenta MCP)

A ferramenta `crawl` aceita os seguintes parâmetros:

| Parâmetro | Tipo | Descrição | Valor Padrão |
|-----------|------|-------------|--------------|
| `url` | string | URL para rastrear (obrigatório) | - |
| `max_depth` | integer | Profundidade de links a seguir (0-5): 0 = apenas a página inicial, 1 = os seus links, etc. | 2 |
| `max_pages` | integer | Número máximo de páginas a rastrear (1-500) | 50 |
| `include_external` | boolean | Incluir links externos | false |
| `wait_for_selector` | string | Seletor CSS a aguardar antes de extrair o conteúdo. Útil para aplicações de página única (SPA). | None |
| `return_content` | boolean | Se deve retornar o conteúdo extraído diretamente na resposta MCP (truncado para 50k caracteres se necessário). | true |
| `max_content_chars` | integer | Número máximo de caracteres de conteúdo retornados na resposta | 50000 |
| `output_file` | string | Nome do arquivo Markdown, sempre salvo no diretório de resultados | gerado automaticamente |
| `overwrite` | boolean | Permitir substituir um `output_file` existente | false |
| `magic` | boolean | Habilitar modo mágico para contornar anti-bots e simular um navegador real | false |
| `css_selector` | string | Seletor CSS específico para extrair apenas elementos direcionados da página | None |
| `js_code` | string | Código JavaScript personalizado para executar na página antes da extração | None |
| `session_id` | string | Identificador de sessão persistente para manter cookies e estado do navegador entre solicitações | None |
| `delay_before_return_html` | number | Atraso em segundos para aguardar antes de extrair o HTML (útil para páginas JS pesadas) | None |

## 📄 Licença

Este projeto está licenciado sob a Licença MIT.

---

> 🏠 **Código-fonte e documentação**: [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
