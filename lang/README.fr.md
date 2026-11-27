# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ Le [README anglais](../README.md) est la version de référence (variables d'environnement, sécurité, développement).

Un puissant outil de crawling web qui s'intègre aux assistants IA via le MCP (Model Context Protocol). Ce projet permet aux assistants IA de crawler des sites web, d'extraire du contenu dynamique, de naviguer à travers les liens et d'enregistrer directement des fichiers Markdown structurés.

## 📋 Fonctionnalités

- Intégration native avec les assistants IA via MCP (`crawl`, `crawl_page`, `close_session`, `open_crawl_explorer`, `view_crawl_file`)
- Renvoie directement le contenu Markdown extrait à l'IA et expose les résultats sauvegardés en ressources MCP (`crawl://results/...`)
- Extrait et met en évidence les liens internes/externes pour la navigation de l'IA
- Crawling de sites web avec profondeur et nombre de pages configurables, notifications de progression en direct et statistiques détaillées
- **MCP Apps interactives (Antigravity / SEP-1865)** — pré-embarquées dans la wheel (sans Node.js) :
  - **Cartes inline** sur `crawl` et `crawl_page` (statut, compteurs, aperçu Markdown rendu/brut, liens filtrables, pages ignorées)
  - **Crawl4AI Explorer** (`open_crawl_explorer`, panneau latéral & pleine page) : résultats paginés, recherche par nom/URL et **recherche plein texte**, **sommaire par page** (copier/attacher une seule page), lanceur de crawl et gestion des sessions
  - **File Viewer dédié** (`view_crawl_file` pour `.crawlmd` / `.crawl.md`) : sommaire par page, métadonnées et recrawl en un clic
  - 100 % rétrocompatible en texte brut pour les clients MCP sans UI

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="Aperçu des MCP Apps Crawl4AI dans Antigravity : carte inline et panneau Crawl4AI Explorer" width="900"/>
</div>

- Gestion des erreurs et des pages introuvables
- **Capacités de Scraping Avancées** :
  - **Filtrage d'URL par motifs glob** : ciblez ou excluez des chemins avec `include_patterns` et `exclude_patterns`
  - **Mode Magique (Magic Mode)** : heuristiques crawl4ai qui simulent un vrai navigateur et aident face à certaines protections anti-bot
  - **Extraction Ciblée** : récupérez uniquement ce dont vous avez besoin à l'aide de sélecteurs CSS
  - **JavaScript Personnalisé** (opt-in) : exécutez du code avant l'extraction (`CRAWL4AI_MCP_ALLOW_JS=true`)
  - **Sessions Persistantes** : un navigateur partagé conserve les cookies et l'état entre les appels (`session_id`)
  - **Prise en charge des SPA** : attendez des sélecteurs CSS dynamiques ou définissez des délais explicites avant l'extraction

## 🚀 Configuration MCP

Le moyen le plus simple et recommandé d'utiliser cet outil est via `uvx`. Le suffixe `@latest` garantit que `uvx` exécute la dernière version publiée sur PyPI.

### Prérequis

- [uv](https://github.com/astral-sh/uv) installé sur votre système.

### Configuration pour les Assistants IA (Claude Desktop, Cline, Antigravity)

Ajoutez ce qui suit au fichier de configuration MCP de votre Assistant IA (`cline_mcp_settings.json`, `claude_desktop_config.json` ou `mcp_config.json`) :

> **Note** : Python 3.12 ou 3.13 est requis. Spécifier `--python 3.13` est fortement recommandé, surtout sous Windows.

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

**Claude Code :**

```bash
claude mcp add crawl -s user -- uvx --python 3.13 crawl4ai-mcp-llm@latest
```

**Google Antigravity (plugin avec MCP Apps) :**

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

### Important : Installation du Navigateur

Le crawler utilise Playwright pour gérer le contenu dynamique. Installez Chromium une fois après avoir configuré l'outil :

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## 🖥️ Utilisation

Une fois configuré, vous pouvez utiliser le crawler en demandant à votre assistant IA d'effectuer un crawl.

### Exemples d'Utilisation

- **Page Unique** : « Lis https://docs.python.org/3/library/re.html (juste cette page) et résume-la. »
- **Crawl Simple** : « Peux-tu crawler le site example.com et me faire un résumé ? »
- **Crawl avec Options** : « Peux-tu crawler https://example.com avec une profondeur de 3 et inclure les liens externes ? »
- **Filtrage d'URL** : « Crawl https://example.com avec `include_patterns=['/docs/*']` et `exclude_patterns=['/docs/legacy/*', '*.pdf']`. »
- **Contenu Dynamique** : « Crawl cette application React et attends que le sélecteur `.main-content` soit chargé. »
- **Extraction Ciblée** : « Crawl le site de docs mais n'extrais que le contenu correspondant au sélecteur CSS `h1, p.lead`. »
- **Explorateur Interactif (Antigravity)** : « Ouvre Crawl4AI Explorer pour rechercher dans mes crawls sauvegardés. »

## 🛠️ Paramètres Disponibles (Outil `crawl`)

L'outil `crawl` accepte les paramètres suivants :

| Paramètre | Type | Description | Valeur par Défaut |
|-----------|------|-------------|---------------|
| `url` | string | URL http(s) à crawler (requis) | - |
| `max_depth` | integer | Profondeur de liens à suivre (0-5) : 0 = page de départ uniquement, 1 = ses liens, etc. | 2 |
| `max_pages` | integer | Nombre maximal de pages à crawler (1-500) | 50 |
| `include_external` | boolean | Inclure les liens externes | false |
| `wait_for_selector` | string | Sélecteur CSS à attendre avant d'extraire le contenu. Utile pour les SPA. | None |
| `return_content` | boolean | Indique s'il faut renvoyer le contenu extrait directement dans la réponse MCP | true |
| `max_content_chars` | integer | Nombre maximal de caractères de contenu renvoyés dans la réponse (1 000-500 000) | 50000 |
| `output_file` | string | Nom du fichier Markdown, toujours enregistré dans le dossier de résultats | généré automatiquement |
| `overwrite` | boolean | Autoriser le remplacement d'un `output_file` existant | false |
| `magic` | boolean | Activer le mode magique crawl4ai (heuristiques anti-bot) | false |
| `css_selector` | string | Sélecteur CSS spécifique pour extraire uniquement les éléments ciblés de la page | None |
| `js_code` | string | Code JavaScript personnalisé à exécuter avant l'extraction (`CRAWL4AI_MCP_ALLOW_JS=true`) | None |
| `session_id` | string | Identifiant de session persistant pour conserver cookies et état du navigateur | None |
| `delay_before_return_html` | number | Délai en secondes (0-60) avant d'extraire le HTML (pages lourdes en JS) | None |
| `include_patterns` | array of strings | Ne suivre que les URL correspondant à au moins un motif glob (ex. `["/docs/*", "*/api/*"]`) | None |
| `exclude_patterns` | array of strings | Ignorer les URL correspondant à un motif glob (ex. `["/blog/*", "*.pdf"]`) ; prioritaire sur `include_patterns` | None |

## 📄 Licence

Ce projet est sous licence MIT.

---

> 🏠 **Code source & documentation** : [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
