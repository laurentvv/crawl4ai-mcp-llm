# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.jpg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ Le [README anglais](../README.md) est la version de référence (variables d'environnement, sécurité, développement).

Un puissant outil de crawling web qui s'intègre aux assistants IA via le MCP (Model Context Protocol). Ce projet permet aux assistants IA de crawler des sites web, d'extraire du contenu dynamique, de naviguer à travers les liens et d'enregistrer directement des fichiers Markdown structurés.

## 📋 Fonctionnalités

- Intégration native avec les assistants IA via MCP
- Renvoie directement le contenu Markdown extrait à l'IA
- Extrait et met en évidence les liens internes/externes pour la navigation de l'IA
- Crawling de sites web avec profondeur configurable
- Statistiques détaillées des résultats de crawling
- Gestion des erreurs et des pages introuvables
- **Capacités de Scraping Avancées** :
  - **Mode Magique (Magic Mode)** : Contourne les anti-bots (comme Cloudflare) et simule le comportement d'un vrai navigateur
  - **Extraction Ciblée** : Récupérez uniquement ce dont vous avez besoin à l'aide de sélecteurs CSS
  - **JavaScript Personnalisé** : Exécutez du code avant l'extraction (clics, défilements, remplissage de formulaires)
  - **Sessions Persistantes** : Conservez les cookies et l'état entre les requêtes pour les sites authentifiés
  - **Prise en charge des SPA** : Attendez des sélecteurs CSS dynamiques ou définissez des délais explicites avant l'extraction

## 🚀 Configuration MCP

Le moyen le plus simple et recommandé d'utiliser cet outil est via `uvx`, qui récupère et exécute automatiquement la dernière version publiée depuis PyPI.

### Prérequis

- [uv](https://github.com/astral-sh/uv) installé sur votre système.

### Configuration pour les Assistants IA (par exemple, Claude Desktop, Cline)

Ajoutez ce qui suit au fichier de configuration MCP de votre Assistant IA (par exemple, `cline_mcp_settings.json` ou `claude_desktop_config.json`) :

> **Note pour les Utilisateurs Windows** : Il est fortement recommandé de spécifier `--python 3.13` pour éviter les problèmes de compilation avec certaines dépendances.

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

### Important : Installation du Navigateur

Le crawler utilise Playwright pour gérer le contenu dynamique. Vous devez installer les navigateurs requis après avoir configuré l'outil :

```bash
uvx --from crawl4ai-mcp-llm playwright install chromium
```

## 🖥️ Utilisation

Une fois configuré, vous pouvez utiliser le crawler en demandant à votre assistant IA d'effectuer un crawl.

### Exemples d'Utilisation avec Claude/Cline

- **Crawl Simple** : « Peux-tu crawler le site example.com et me faire un résumé ? »
- **Crawl avec Options** : « Peux-tu crawler https://example.com avec une profondeur de 3 et inclure les liens externes ? »
- **Contenu Dynamique** : « Crawl cette application React et attends que le sélecteur `.main-content` soit chargé. »
- **Contourner les Protections** : « Crawl example.com mais utilise le « mode magique » (magic mode) pour contourner la protection anti-bot. »
- **Extraction Ciblée** : « Crawl le site de docs mais n'extrais que le contenu correspondant au sélecteur CSS `h1, p.lead`. »

## 🛠️ Paramètres Disponibles (Outil MCP)

L'outil `crawl` accepte les paramètres suivants :

| Paramètre | Type | Description | Valeur par Défaut |
|-----------|------|-------------|---------------|
| `url` | string | URL à crawler (requis) | - |
| `max_depth` | integer | Profondeur de liens à suivre (0-5) : 0 = page de départ uniquement, 1 = ses liens, etc. | 2 |
| `max_pages` | integer | Nombre maximal de pages à crawler (1-500) | 50 |
| `include_external` | boolean | Inclure les liens externes | false |
| `wait_for_selector` | string | Sélecteur CSS à attendre avant d'extraire le contenu. Utile pour les applications monopages (SPA). | None |
| `return_content` | boolean | Indique s'il faut renvoyer le contenu extrait directement dans la réponse MCP (tronqué à 50 000 caractères si nécessaire). | true |
| `max_content_chars` | integer | Nombre maximal de caractères de contenu renvoyés dans la réponse | 50000 |
| `output_file` | string | Nom du fichier Markdown, toujours enregistré dans le dossier de résultats | généré automatiquement |
| `overwrite` | boolean | Autoriser le remplacement d'un `output_file` existant | false |
| `magic` | boolean | Activer le mode magique pour contourner les anti-bots et simuler un vrai navigateur | false |
| `css_selector` | string | Sélecteur CSS spécifique pour extraire uniquement les éléments ciblés de la page | None |
| `js_code` | string | Code JavaScript personnalisé à exécuter sur la page avant l'extraction | None |
| `session_id` | string | Identifiant de session persistant pour conserver les cookies et l'état du navigateur entre les requêtes | None |
| `delay_before_return_html` | number | Délai en secondes à attendre avant d'extraire le HTML (utile pour les pages lourdes en JS) | None |

## 📄 Licence

Ce projet est sous licence MIT.

---

> 🏠 **Code source & documentation** : [github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
