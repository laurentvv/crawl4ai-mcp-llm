# PLAN.md — Audit de `crawl4ai-mcp-llm` (v0.1.6)

> Périmètre audité : `src/crawl4ai_mcp_llm/` (≈590 lignes), `tests/` (11 fichiers), `pyproject.toml`, `uv.lock`, `pytest.ini`, `README*.md`, `lang/`, `.github/`.
> Vérifications effectuées dans un environnement isolé (`uv sync --frozen`, Python 3.13, crawl4ai 0.9.2, mcp 2.0.0) : 39 tests unitaires passent ; les constats marqués ✅ ont été reproduits.

---

## 1. Diagnostic

**Bloquant**
- ✅ `src/crawl4ai_mcp_llm/server.py:27` — la « docstring » du tool `crawl` est une **f-string**, que Python n'enregistre pas comme docstring : `crawl.__doc__ is None` et `list_tools()` expose une **description vide**. Le LLM client ne voit ni les avertissements de performance ni les conseils d'usage.
- ✅ `src/crawl4ai_mcp_llm/crawler.py:121-123` — aucune validation du schéma d'URL : crawl4ai accepte `file://` et `raw:`, un LLM (ou une injection de prompt dans une page crawlée) peut donc lire `file:///etc/passwd`, `~/.ssh/…` ou viser le réseau interne (`localhost`, `169.254.169.254`). Surface SSRF / lecture locale non maîtrisée.
- ✅ `src/crawl4ai_mcp_llm/crawler.py:104-115` — le verrou `CRAWL4AI_MCP_ALLOW_JS` se contourne via `wait_for_selector="js:() => …"` (crawl4ai évalue le préfixe `js:` dans la page).

**Important**
- `crawler.py:122` — un `AsyncWebCrawler` (donc un Chromium) est lancé puis détruit **à chaque appel** : démarrage lent, et `session_id` (« Persistent Sessions » dans le README) n'a **aucun effet** d'un appel à l'autre.
- ✅ `crawler.py:58-73` + `server.py:38` — la sémantique de `max_depth` est fausse : dans `BFSDeepCrawlStrategy`, la page de départ est à la profondeur 0, donc `max_depth=1` suit déjà les liens directs (le message « Use 1 for a single page » induit en erreur).
- ✅ `crawler.py:25-28` — `ERROR_INDICATORS_REGEX` écarte des pages légitimes (« Forbidden Planet (1956) - Wikipedia » est comptée comme 403) ; ✅ `crawler.py:179` plante (`AttributeError`) si `result.metadata is None`.
- Pas de timeout global ni de limite de pages par défaut (`max_pages=None`), pas de CI, pas de lint/typage, erreurs renvoyées comme texte `"Error: …"` au lieu de `isError` MCP.

**Mineur**
- Journalisation par `print(..., file=sys.stderr)` sans niveaux ; fichier `test_ansible.log` versionné ; `tests/test_path_validation.py` laisse un lien symbolique `crawl_results/evil -> /` ; doc incohérente (dossier de résultats, `max_pages` absent, installation Playwright via `uvx`).

---

> **Suivi — refactoring appliqué (section 2).** Toutes les tâches de la section 2 sont traitées, à une exception près : `ctx.info()`, remplacé par la liste des pages ignorées dans la réponse du tool, car la capacité de logging MCP est dépréciée. Des précisions accompagnent certaines tâches.
> Vérifications : 118 tests unitaires (couverture 89 %, seuil 80 %) sous Python 3.12 et 3.13, `ruff check`, `ruff format --check` et `mypy` propres, `pip-audit` propre (une exception documentée). Validé aussi par un test de fumée du serveur stdio via le client MCP, et par un vrai crawl Chromium sur un site local (streaming, 404, réutilisation du navigateur, filtrage `file://`).
> **Suivi — nouvelles fonctionnalités (section 3) implémentées.** Progression MCP page par page, annulation propre, sessions de navigateur avec `close_session` et expiration, tool `crawl_page`, ressources `crawl://results` et `crawl://results/{+path}`. 140 tests (couverture 90 %) ; vérifié de bout en bout via le client MCP stdio et un vrai Chromium sur un site local (notifications de progression reçues, lecture de ressource, traversée de chemin bloquée).

---

## 2. Checklist de Refactoring

### Sécurité
- [x] [P0] `src/crawl4ai_mcp_llm/crawler.py` — Ajouter une fonction `validate_url()` appelée avant `crawler.arun()` : n'accepter que `http`/`https`, rejeter `file://`, `raw:`, `data:`, `javascript:` et les hôtes vides ; renvoyer une erreur explicite.
- [x] [P0] `src/crawl4ai_mcp_llm/crawler.py` — Bloquer par défaut les cibles privées (loopback, RFC1918, link-local, `169.254.169.254`, `::1`) après résolution DNS, avec opt-in via une variable `CRAWL4AI_MCP_ALLOW_PRIVATE_NETWORKS=true`.
- [x] [P0] `src/crawl4ai_mcp_llm/crawler.py:104-105` — Refuser `wait_for_selector` préfixé par `js:` (ou non préfixé mais contenant `=>`/`function`) quand `CRAWL4AI_MCP_ALLOW_JS` n'est pas activé ; forcer le préfixe `css:` sinon.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py:80-90` — Imposer l'extension `.md` sur `output_file`, refuser l'écrasement d'un fichier existant (ou ajouter un paramètre `overwrite`), et normaliser les noms (pas de `:` ni de séparateurs).
- [x] [P1] `src/crawl4ai_mcp_llm/server.py:105` — Encadrer le contenu crawlé renvoyé au LLM par des délimiteurs explicites (« contenu non fiable provenant du web ») pour limiter l'injection de prompt indirecte.
- [x] [P2] `src/crawl4ai_mcp_llm/server.py:11` — Déclarer des `ToolAnnotations` (`readOnlyHint=False`, `openWorldHint=True`, `destructiveHint=False`) pour que les clients MCP appliquent une politique de confirmation adaptée.

### Contrat du tool MCP
- [x] [P0] `src/crawl4ai_mcp_llm/server.py:27-46` — Remplacer la f-string par une docstring littérale (ou passer `description=` à `@app.tool(...)`) ; ajouter un test qui vérifie que `list_tools()[0].description` est non vide et mentionne `CRAWL4AI_MCP_ALLOW_JS`.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py:58-73`, `server.py:38` — Aligner la sémantique de `max_depth` sur crawl4ai (0 = page seule) ou convertir explicitement (`max_depth - 1`), puis corriger le message d'erreur et la docstring. — Sémantique crawl4ai retenue (0 = page seule) : non cassant, les valeurs ≥ 1 gardent leur comportement.
- [x] [P1] `src/crawl4ai_mcp_llm/server.py:63-64,108-111` — Lever `mcp.server.mcpserver.exceptions.ToolError` au lieu de renvoyer `"Error: …"` pour que le client reçoive `isError=True`.
- [x] [P1] `src/crawl4ai_mcp_llm/server.py:95-106` — Ne plus annoncer « Crawl completed successfully » quand `successful_pages == 0` ; retirer la phrase « stored in the 'crawl_results' folder of your project » (le dossier réel est `~/.crawl4ai_mcp_llm/results` ou `CRAWL4AI_RESULTS_DIR`).
- [x] [P1] `src/crawl4ai_mcp_llm/server.py:12-26` — Contraindre les paramètres via `Annotated[int, Field(ge=0, le=5)]` pour `max_depth`, `Field(ge=1, le=500)` pour `max_pages`, `Field(ge=0, le=60)` pour `delay_before_return_html`, et fixer une valeur par défaut raisonnable pour `max_pages`.
- [x] [P2] `src/crawl4ai_mcp_llm/server.py:14,87` — Supprimer le paramètre `verbose` du contrat exposé au LLM (réglage opérateur, pas LLM) et rendre `max_chars` (50 000) configurable (`max_content_chars`).
- [x] [P2] `src/crawl4ai_mcp_llm/server.py:9` — Lire la version depuis `importlib.metadata.version("crawl4ai-mcp-llm")` au lieu de dupliquer `"0.1.6"` de `pyproject.toml`.

### Gestion des erreurs et robustesse
- [x] [P0] `src/crawl4ai_mcp_llm/crawler.py:179-181` — Protéger `_format_markdown_page` contre `metadata is None` via un helper unique `_get_title(result)` / `_get_meta(result, key, default)`.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py:162,244` — Supprimer la duplication de l'extraction du titre et de la regex : faire renvoyer par `_extract_page_content_and_errors` la raison de détection (`status_code`, `nginx`, `title`) plutôt que recalculer dans `results_to_markdown`.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py:25-28,157,164` — Restreindre la détection d'erreur par titre aux titres courts **commençant** par `404`/`403`/`Not Found`/`Forbidden`/`Page not found`, s'appuyer d'abord sur `status_code`, et rendre la comparaison `"Not Found"` insensible à la casse.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py:121-123` — Envelopper le crawl dans `anyio.fail_after(timeout)` (timeout configurable, défaut ≈ 300 s) et renvoyer des résultats partiels si possible.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py:30-39,225-231` — Remplacer les dicts libres par des `TypedDict`/`dataclass` (`CrawlStats`, `CrawlOutcome`) et réutiliser `_empty_stats()` dans `results_to_markdown` ; exclure `start_time`/`end_time` (objets `datetime`) du résultat ou les sérialiser.
- [x] [P2] `src/crawl4ai_mcp_llm/utils.py:72-82` — Rendre `generate_filename_from_url` sûr sur Windows (remplacer `:`), gérer les URL sans schéma et ajouter un suffixe unique (ms ou `uuid4().hex[:6]`) contre les collisions dans la même seconde.
- [x] [P2] `src/crawl4ai_mcp_llm/cli.py:8-19` — Déplacer le `try/except` dans `main()` (le bloc `__main__` n'est jamais exécuté via l'entry point) et supprimer le `return 0` ignoré par Click.

### Structure des modules
- [x] [P1] `src/crawl4ai_mcp_llm/` — Créer `config.py` (settings centralisés : `RESULTS_DIR`, `ALLOW_JS`, `ALLOW_PRIVATE_NETWORKS`, timeouts, limites) lu une fois au démarrage, au lieu de `os.getenv` dispersés dans `crawler.py` et `utils.py`. — Les réglages sont relus à chaque appel (`get_settings()`), ce qui reste bon marché et permet de surcharger l'environnement dans les tests.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py` — Scinder en `crawler.py` (orchestration crawl4ai), `markdown.py` (formatage/nettoyage, actuellement réparti entre `crawler.py` et `utils.py`) et `security.py` (validation URL/chemins/JS). — `utils.py` conserve `sanitize_for_display` et la génération de noms de fichiers.
- [x] [P2] `src/crawl4ai_mcp_llm/__init__.py` — Supprimer le remplacement de `sys.stdout`/`sys.stderr` à l'import (effet de bord global sur tout importeur, y compris les tests) ; si nécessaire, le faire dans `cli.main()` pour `stderr` uniquement (le transport stdio MCP gère déjà `stdout`).
- [x] [P2] `.github/copilot-instructions.md` — Remplacer le prompt générique par des consignes propres au projet (conventions, commandes de test, règles de sécurité) ou le supprimer.

### Performance et concurrence
- [x] [P1] `src/crawl4ai_mcp_llm/server.py`, `crawler.py:122` — Créer un `AsyncWebCrawler` partagé dans un `lifespan` de `MCPServer` (démarré au boot, fermé à l'arrêt) pour supprimer le coût de démarrage Chromium par appel et rendre `session_id` réellement persistant.
- [x] [P1] `src/crawl4ai_mcp_llm/crawler.py` — Limiter la concurrence des appels `crawl` via un `anyio.CapacityLimiter` (ex. 2) pour éviter plusieurs navigateurs/crawls lourds simultanés.
- [x] [P1] `src/crawl4ai_mcp_llm/server.py:82-89` — Ne plus relire depuis le disque le fichier que l'on vient d'écrire : faire renvoyer par `results_to_markdown` le contenu (ou ses N premiers caractères) accumulé en mémoire.
- [x] [P2] `src/crawl4ai_mcp_llm/crawler.py:236-257` — Exécuter le nettoyage Markdown (regex CPU-bound sur des pages volumineuses) via `anyio.to_thread.run_sync` pour ne pas bloquer la boucle d'événements.
- [x] [P2] `src/crawl4ai_mcp_llm/crawler.py:93-102` — Utiliser `stream=True` de crawl4ai pour écrire chaque page dès sa réception au lieu de garder tous les résultats en mémoire.

### Tests
- [x] [P0] `tests/test_path_validation.py` — Réécrire avec `tmp_path` et de vrais `assert` (pas de `print` + `sys.exit`) ; ne plus créer `crawl_results/evil -> /` dans le répertoire courant.
- [x] [P1] `tests/test_performance.py` — Supprimer l'assertion temporelle (`opt_time < orig_time * 0.7`), instable en CI ; conserver uniquement le test d'équivalence ou le déplacer en benchmark optionnel (`pytest-benchmark`).
- [x] [P1] `tests/test_results.py`, `tests/test_security_js.py` — Isoler les écritures disque via `tmp_path` et `monkeypatch.setenv("CRAWL4AI_RESULTS_DIR", …)` (aujourd'hui écriture dans le CWD et création de `~/.crawl4ai_mcp_llm/results`).
- [x] [P1] `tests/` — Ajouter des tests du tool `crawl` de `server.py` (résumé, échantillon de liens, troncature à 50 000 caractères, `return_content=False`, chemin d'erreur) : aucun n'existe aujourd'hui.
- [x] [P1] `tests/` — Ajouter des tests de sécurité : rejet de `file://`, `raw:`, IP privées, `wait_for_selector="js:…"`, `output_file` hors du dossier de résultats (absolu et relatif `../`).
- [x] [P1] `pytest.ini` / `pyproject.toml` — Enregistrer le marqueur `integration`, l'exclure par défaut (`addopts = -m "not integration"`), définir `testpaths = tests` et `pythonpath = src` ; supprimer les manipulations `sys.path` dans les tests.
- [x] [P2] `tests/run_all_tests.py`, tests `unittest` — Uniformiser sur pytest (fixtures, `parametrize`) et supprimer le runner `unittest` redondant.
- [x] [P2] `tests/test_extract_unique_links.py:109-124`, `tests/test_filename.py:33-43` — Remplacer les tests qui figent des bugs (`pytest.raises(Exception)` générique, `crawl_localhost:8080_…`) par le comportement attendu une fois corrigé.
- [x] [P2] `pyproject.toml` — Ajouter `pytest-cov` et un seuil de couverture minimal (ex. 80 % sur `src/`).

### Dépendances et outillage
- [x] [P1] `pyproject.toml:6` — Élargir `requires-python` à `>=3.12` (ou au minimum retirer `<3.14`) et tester la matrice 3.12/3.13/3.14 ; aligner le badge README « 3.13+ ». — Fait partiellement : `>=3.12,<3.14`. Python 3.14 reste exclu car crawl4ai 0.9.2 ne s'importe pas sous 3.14 (incompatibilité pydantic en amont) ; CI sur 3.12/3.13.
- [x] [P1] `pyproject.toml:8-17` — Retirer les dépendances non importées directement (`chardet`, `httpx`, `lxml`, `urllib3`) — elles viennent transitivement de crawl4ai — et relever le plancher `crawl4ai>=0.9` (version verrouillée et testée dans `uv.lock`, dont le logger écrit sur stderr).
- [x] [P1] `.github/workflows/ci.yml` (à créer) — Pipeline `uv sync --frozen`, `ruff check`, `ruff format --check`, `mypy`/`pyright`, `pytest` ; job d'intégration séparé et manuel/nocturne.
- [x] [P1] `.github/workflows/release.yml` (à créer) — Publication PyPI par Trusted Publishing sur tag, avec vérification de cohérence tag ↔ version. — Nécessite de déclarer le Trusted Publisher (environnement `pypi`) côté PyPI avant le premier tag.
- [x] [P2] `pyproject.toml:37-38` — Étendre la config Ruff (`select = ["E","F","I","B","UP","ASYNC","S"]`) et retirer l'ignore `E402`, rendu inutile une fois les hacks `sys.path` supprimés.
- [x] [P2] `.github/dependabot.yml` (à créer) — Activer les mises à jour `uv` et `github-actions` + `pip-audit` en CI. — `pip-audit` bloquant en CI ; PYSEC-2026-3740 (nltk, sans correctif publié, API non utilisée) ignorée explicitement.

### Observabilité
- [x] [P1] `src/crawl4ai_mcp_llm/*.py` — Remplacer tous les `print(..., file=sys.stderr)` par `logging.getLogger(__name__)` configuré sur stderr dans `cli.main()`, niveau réglable via `CRAWL4AI_MCP_LOG_LEVEL`.
- [ ] [P1] `src/crawl4ai_mcp_llm/server.py` — Injecter `Context` dans le tool et utiliser `ctx.info()`/`ctx.warning()` pour remonter au client MCP les pages ignorées et les erreurs. — **Non fait** : la capacité de logging MCP (`ctx.info()`/`ctx.warning()`) est dépréciée depuis la spec 2026-07-28 (SEP-2577). Les pages ignorées et leur raison figurent désormais dans la réponse du tool (section « Skipped Pages »).
- [x] [P2] `src/crawl4ai_mcp_llm/crawler.py:131-133,277-279` — Ne plus journaliser la trace complète à chaque erreur réseau attendue (timeout, DNS) ; réserver `logger.exception` aux erreurs inattendues.

### Documentation et hygiène du dépôt
- [x] [P1] `README.md`, `README_PYPI.md`, `lang/*.md` — Ajouter `max_pages` au tableau des paramètres, documenter `CRAWL4AI_RESULTS_DIR` et `CRAWL4AI_MCP_ALLOW_JS`, préciser la contrainte de `output_file` (dossier de résultats) et corriger la sémantique de `max_depth`. — Les traductions reçoivent le tableau de paramètres et la commande d'installation corrigés ; les sections variables d'environnement et sécurité sont en anglais uniquement.
- [x] [P1] `README.md` (« Browser Installation ») — Remplacer `uv run playwright install chromium` (inopérant pour un utilisateur `uvx`) par `uvx --from crawl4ai-mcp-llm playwright install chromium` (ou `crawl4ai-setup`).
- [x] [P1] `README.md` (« Persistent Sessions », « Magic Mode ») — Corriger les promesses : `session_id` ne persiste pas entre appels tant que le crawler n'est pas partagé ; nuancer « bypass Cloudflare ».
- [x] [P2] `test_ansible.log` — Supprimer ce fichier versionné (déjà couvert par `*.log` dans `.gitignore`).
- [x] [P2] `lang/*.md` — Générer les traductions à partir d'une source unique (ou indiquer la version de référence) pour éviter la dérive avec `README.md`. — Chaque traduction renvoie au README anglais comme version de référence.
- [x] [P2] `CHANGELOG.md` (à créer) — Tenir un changelog (Keep a Changelog) aligné sur les versions PyPI.

---

## 3. Checklist de Nouvelles Fonctionnalités

### 3.1 Progression en temps réel et crawl en streaming

- [x] Ajouter un paramètre `ctx: Context` au tool `crawl` dans `server.py`
- [x] Passer `stream=True` à `CrawlerRunConfig` et itérer avec `async for result in await crawler.arun(...)`
- [x] Appeler `ctx.report_progress(done, total=max_pages, message=url)` à chaque page traitée
- [x] Écrire chaque page dans le fichier Markdown au fil de l'eau (refonte de `results_to_markdown` en consommateur incrémental)
- [x] Gérer l'annulation côté client (`anyio.get_cancelled_exc_class()`) en finalisant proprement le fichier partiel — La fermeture du fichier est protégée contre l'annulation (sinon le contenu n'était jamais écrit sur disque) et un marqueur signale le résultat partiel.
- [x] Tests : faux crawler émettant un générateur asynchrone + vérification des appels `report_progress`
- [x] Documenter dans le README que le timeout client peut être réduit si le client gère la progression

**Approche technique**
Le principal irritant documenté du projet (docstring et README) est la durée des crawls (« 30 s à plusieurs minutes », timeout de 600 s conseillé). `MCPServer` 2.0 fournit déjà `Context.report_progress()` ; beaucoup de clients réarment leur timeout à chaque notification de progression. crawl4ai supporte nativement `stream=True` avec `BFSDeepCrawlStrategy`, ce qui supprime aussi l'accumulation de tous les résultats en mémoire. La logique de `results_to_markdown` devient une boucle `async for` qui réutilise `_extract_page_content_and_errors` et `_format_markdown_page` sans changement. Écarté : un mécanisme maison de polling (`start_crawl` / `get_status`), plus complexe et redondant avec le protocole MCP.

### 3.2 Crawler partagé via `lifespan` + tool de gestion des sessions

- [x] Définir un `lifespan` asynchrone dans `server.py` qui instancie un `AsyncWebCrawler` (via `BrowserConfig`) et le ferme proprement
- [x] Exposer le crawler au tool via `ctx.request_context.lifespan_context` — `_manager(ctx)` lit l'instance dans `ctx.request_context.lifespan_context` (repli sur l'instance du module hors requête, p. ex. dans les tests).
- [x] Ajouter un tool `close_session(session_id)` appelant `crawler.crawler_strategy.kill_session()`
- [x] Ajouter une expiration des sessions inactives (TTL configurable) pour libérer les onglets — Expiration paresseuse (vérifiée au début de chaque crawl), sans tâche de fond ; `CRAWL4AI_MCP_SESSION_TTL`, 1800 s par défaut.
- [x] Protéger l'accès concurrent par un `anyio.CapacityLimiter`
- [x] Tests : vérifier qu'un seul navigateur est démarré pour deux appels consécutifs et que `session_id` est bien réutilisé

**Approche technique**
Le README promet des « Persistent Sessions » alors que `crawler.py` recrée le navigateur à chaque appel, ce qui annule `session_id` et coûte plusieurs secondes de démarrage Chromium. Le paramètre `lifespan` de `MCPServer` est le point d'extension idiomatique : une ressource longue durée partagée entre appels, fermée à l'arrêt du process stdio. crawl4ai gère déjà les sessions par `session_id` dans son `browser_manager` ; il suffit de conserver l'instance. Le démarrage paresseux (au premier appel) est préférable à un démarrage au boot pour ne pas ralentir `initialize` côté client. Écarté : un pool externe (serveur Playwright distant), disproportionné pour un serveur MCP local.

### 3.3 Exposition des résultats en ressources MCP + tool `crawl_page` léger

- [x] Déclarer une ressource template `crawl://results/{filename}` renvoyant un fichier du dossier de résultats (validé par `is_safe_path`)
- [x] Déclarer une ressource `crawl://results` listant les fichiers (nom, URL source, date, taille)
- [x] Ajouter un tool `crawl_page(url, css_selector=None)` : une seule page (`max_depth=0`), sans écriture disque, contenu renvoyé directement
- [x] Réduire la réponse de `crawl` à un résumé + URI de ressource quand le contenu dépasse la limite, au lieu de tronquer — Variante retenue : la réponse garde un aperçu tronqué **et** indique l'URI de ressource, pour rester utile aux clients qui ne lisent pas les ressources.
- [x] Tests : lecture de ressource, rejet de traversée de chemin (`../`), `crawl_page` avec crawler simulé

**Approche technique**
Aujourd'hui le contenu est tronqué à 50 000 caractères et le reste n'est accessible qu'en lisant le fichier hors MCP, ce qui échoue quand le client n'a pas accès au système de fichiers du serveur. Les ressources MCP (`@app.resource`) sont le mécanisme prévu pour exposer des documents volumineux que le client charge à la demande ; elles réutilisent `get_results_directory()` et `is_safe_path()` existants. Le tool `crawl_page` couvre le cas le plus fréquent (« lis cette page ») avec un contrat simple, ce qui limite les erreurs du LLM sur `max_depth`/`max_pages` constatées dans la docstring actuelle. Écarté : renvoyer le contenu complet paginé via un paramètre `offset`, moins naturel que les ressources et plus coûteux en appels de tool.
