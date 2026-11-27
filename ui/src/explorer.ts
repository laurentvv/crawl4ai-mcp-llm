import { App } from '@modelcontextprotocol/ext-apps';
import './styles.css';
import {
  applyThemeFromContext,
  copyToClipboard,
  escapeHtml,
  extractErrorMessage,
  formatBytes,
  formatDate,
  isSafeHttpUrl,
  openFileInAuxPane,
  parseCrawledDocument,
  parsePatternInput,
  renderSafeMarkdown,
  wireExternalLinks,
  type CrawlCardPayload,
  type CrawledPageSection,
  type ExplorerPayload,
  type ListResultsPayload,
  type ReadResultPayload,
  type SavedResultEntry,
  type SearchMatch,
  type SearchResultsPayload,
} from './shared';

const root = document.getElementById('root')!;
const PAGE_SIZE = 200;

interface ExplorerState {
  connected: boolean;
  activeTab: 'results' | 'crawl' | 'sessions';
  results: SavedResultEntry[];
  searchMatches: SearchMatch[];
  searchMode: 'meta' | 'fulltext';
  totalResults: number;
  totalAll: number;
  hasMore: boolean;
  loadingMore: boolean;
  sessions: string[];
  searchQuery: string;
  selectedName: string | null;
  selectedDoc: ReadResultPayload | null;
  docSections: CrawledPageSection[];
  selectedPageIndex: number; // -1 = full document, >=0 = specific crawled page
  loadingList: boolean;
  loadingDoc: boolean;
  docError: string | null;
  renderMode: 'rendered' | 'raw';
  // New crawl form state
  crawlMode: 'crawl_page' | 'crawl';
  formUrl: string;
  formMaxDepth: number;
  formMaxPages: number;
  formCssSelector: string;
  formWaitFor: string;
  formOutputFile: string;
  formIncludePatterns: string;
  formExcludePatterns: string;
  formMagic: boolean;
  formIncludeExternal: boolean;
  formOverwrite: boolean;
  crawling: boolean;
  crawlError: string | null;
  lastCrawlResult: CrawlCardPayload | null;
  statusNote: string;
}

const state: ExplorerState = {
  connected: false,
  activeTab: 'results',
  results: [],
  searchMatches: [],
  searchMode: 'meta',
  totalResults: 0,
  totalAll: 0,
  hasMore: false,
  loadingMore: false,
  sessions: [],
  searchQuery: '',
  selectedName: null,
  selectedDoc: null,
  docSections: [],
  selectedPageIndex: -1,
  loadingList: false,
  loadingDoc: false,
  docError: null,
  renderMode: 'rendered',
  crawlMode: 'crawl_page',
  formUrl: '',
  formMaxDepth: 1,
  formMaxPages: 20,
  formCssSelector: '',
  formWaitFor: '',
  formOutputFile: '',
  formIncludePatterns: '',
  formExcludePatterns: '',
  formMagic: false,
  formIncludeExternal: false,
  formOverwrite: false,
  crawling: false,
  crawlError: null,
  lastCrawlResult: null,
  statusNote: '',
};

let searchTimer: number | undefined;
let listRequestSeq = 0;
let docRequestSeq = 0;

const app = new App({ name: 'Crawl4AI Explorer', version: '1.0.0' }, {});

function flashStatus(message: string): void {
  state.statusNote = message;
  const el = document.getElementById('explorer-toast');
  if (el) el.textContent = message;
  window.setTimeout(() => {
    if (state.statusNote === message) {
      state.statusNote = '';
      const current = document.getElementById('explorer-toast');
      if (current) current.textContent = '';
    }
  }, 2800);
}

function restoreSearchFocus(): void {
  const refocused = document.getElementById('results-search') as HTMLInputElement | null;
  if (refocused) {
    refocused.focus();
    refocused.setSelectionRange(refocused.value.length, refocused.value.length);
  }
}

async function runFullTextSearch(preserveFocus = false): Promise<void> {
  const q = state.searchQuery.trim();
  if (!q) {
    state.searchMatches = [];
    await refreshListing(undefined, preserveFocus);
    return;
  }
  const seq = ++listRequestSeq;
  state.loadingList = true;
  if (!preserveFocus) render();
  try {
    const res = await app.callServerTool({
      name: 'app_search_results',
      arguments: { query: q, limit: 50 },
    });
    if (seq !== listRequestSeq) return;
    if (!res.isError) {
      const data = res.structuredContent as SearchResultsPayload | undefined;
      state.searchMatches = data?.matches ?? [];
    } else {
      flashStatus(extractErrorMessage(res));
    }
  } catch {
    if (seq === listRequestSeq) flashStatus('Full-text search failed');
  } finally {
    if (seq !== listRequestSeq) return;
    state.loadingList = false;
    render();
    if (preserveFocus) restoreSearchFocus();
  }
}

async function refreshListing(selectName?: string, preserveFocus = false): Promise<void> {
  if (state.searchMode === 'fulltext' && state.searchQuery.trim()) {
    await runFullTextSearch(preserveFocus);
    return;
  }
  const seq = ++listRequestSeq;
  state.loadingList = true;
  state.searchMatches = [];
  if (!preserveFocus) render();
  try {
    const args: Record<string, unknown> = { offset: 0, limit: PAGE_SIZE };
    if (state.searchQuery.trim()) args.query = state.searchQuery.trim();
    const res = await app.callServerTool({ name: 'app_list_results', arguments: args });
    if (seq !== listRequestSeq) return;
    if (!res.isError) {
      const data = res.structuredContent as ListResultsPayload | undefined;
      state.results = data?.results ?? [];
      state.totalResults = data?.total_results ?? state.results.length;
      state.totalAll = data?.total_all ?? state.totalResults;
      state.hasMore = Boolean(data?.has_more);
      state.sessions = data?.sessions ?? [];
      if (selectName) {
        state.selectedName = selectName;
      } else if (
        !state.selectedName ||
        (!state.searchQuery.trim() && !state.results.some((r) => r.name === state.selectedName))
      ) {
        state.selectedName = state.results[0]?.name ?? null;
      }
    }
  } catch {
    if (seq === listRequestSeq) flashStatus('Failed to refresh');
  } finally {
    if (seq !== listRequestSeq) return;
    state.loadingList = false;
    render();
    if (preserveFocus) restoreSearchFocus();
    if (!preserveFocus) {
      if (state.selectedName) {
        void loadDocument(state.selectedName);
      } else {
        state.selectedDoc = null;
        state.docSections = [];
        state.selectedPageIndex = -1;
        state.docError = null;
        render();
      }
    }
  }
}

async function loadMoreResults(): Promise<void> {
  if (state.loadingMore || !state.hasMore) return;
  const seq = listRequestSeq;
  state.loadingMore = true;
  render();
  try {
    const args: Record<string, unknown> = { offset: state.results.length, limit: PAGE_SIZE };
    if (state.searchQuery.trim()) args.query = state.searchQuery.trim();
    const res = await app.callServerTool({ name: 'app_list_results', arguments: args });
    if (seq !== listRequestSeq) return;
    if (!res.isError) {
      const data = res.structuredContent as ListResultsPayload | undefined;
      const incoming = data?.results ?? [];
      state.results = [...state.results, ...incoming];
      state.totalResults = data?.total_results ?? state.results.length;
      state.totalAll = data?.total_all ?? state.totalResults;
      state.hasMore = Boolean(data?.has_more);
      state.sessions = data?.sessions ?? state.sessions;
    }
  } catch {
    flashStatus('Failed to load more results');
  } finally {
    state.loadingMore = false;
    render();
  }
}

async function loadDocument(name: string): Promise<void> {
  const seq = ++docRequestSeq;
  state.selectedName = name;
  state.loadingDoc = true;
  state.docError = null;
  state.selectedPageIndex = -1;
  render();
  try {
    const res = await app.callServerTool({
      name: 'app_read_result',
      arguments: { name },
    });
    if (seq !== docRequestSeq) return;
    if (res.isError) {
      state.selectedDoc = null;
      state.docSections = [];
      state.docError = extractErrorMessage(res);
    } else {
      const data = res.structuredContent as ReadResultPayload | undefined;
      state.selectedDoc = data ?? null;
      state.docSections = data ? parseCrawledDocument(data.content) : [];
      if (!data) state.docError = 'Empty result payload.';
    }
  } catch (err) {
    if (seq !== docRequestSeq) return;
    state.selectedDoc = null;
    state.docSections = [];
    state.docError = err instanceof Error ? err.message : 'Failed to read result.';
  } finally {
    if (seq !== docRequestSeq) return;
    state.loadingDoc = false;
    render();
  }
}

async function runCrawlFromForm(): Promise<void> {
  const url = state.formUrl.trim();
  if (!url) {
    state.crawlError = 'Please enter a URL to crawl.';
    render();
    return;
  }
  state.crawling = true;
  state.crawlError = null;
  state.lastCrawlResult = null;
  render();

  const args: Record<string, unknown> = { url };
  if (state.formCssSelector.trim()) args.css_selector = state.formCssSelector.trim();
  if (state.formWaitFor.trim()) args.wait_for_selector = state.formWaitFor.trim();
  if (state.formMagic) args.magic = true;

  if (state.crawlMode === 'crawl') {
    args.max_depth = state.formMaxDepth;
    args.max_pages = state.formMaxPages;
    args.include_external = state.formIncludeExternal;
    if (state.formOutputFile.trim()) args.output_file = state.formOutputFile.trim();
    if (state.formOverwrite) args.overwrite = true;
    const includes = parsePatternInput(state.formIncludePatterns);
    const excludes = parsePatternInput(state.formExcludePatterns);
    if (includes.length) args.include_patterns = includes;
    if (excludes.length) args.exclude_patterns = excludes;
  }

  try {
    const res = await app.callServerTool({ name: state.crawlMode, arguments: args });
    if (res.isError) {
      state.crawlError = extractErrorMessage(res);
    } else {
      const payload = res.structuredContent as CrawlCardPayload | undefined;
      state.lastCrawlResult = payload ?? null;
      flashStatus('Crawl finished');
      if (state.crawlMode === 'crawl') {
        void refreshListing(payload?.result_name ?? undefined);
      }
    }
  } catch (err) {
    state.crawlError = err instanceof Error ? err.message : 'Crawl request failed.';
  } finally {
    state.crawling = false;
    render();
  }
}

async function closeSession(sessionId: string): Promise<void> {
  try {
    const res = await app.callServerTool({
      name: 'close_session',
      arguments: { session_id: sessionId },
    });
    flashStatus(res.isError ? extractErrorMessage(res) : `Closed session "${sessionId}"`);
    await refreshListing();
  } catch {
    flashStatus('Failed to close session');
  }
}

function activePageSection(): CrawledPageSection | null {
  if (state.selectedPageIndex < 0 || state.selectedPageIndex >= state.docSections.length) {
    return null;
  }
  return state.docSections[state.selectedPageIndex];
}

function renderResultsTab(canMessage: boolean, canUpdateContext: boolean, canOpenLinks: boolean): string {
  const isFullText = state.searchMode === 'fulltext' && state.searchQuery.trim().length > 0;

  let listHtml = '';
  if (isFullText) {
    listHtml = state.searchMatches.length
      ? state.searchMatches
          .map(
            (m) => `
            <button class="c4-result-row" data-select-result="${escapeHtml(m.name)}" aria-current="${m.name === state.selectedName}">
              <span class="c4-result-name">${escapeHtml(m.name)}</span>
              <span class="c4-snippet">${escapeHtml(m.snippet)}</span>
              <span class="c4-result-meta">
                <span>${m.match_count} match${m.match_count > 1 ? 'es' : ''} · L${m.line}</span>
                <span>${formatBytes(m.size_bytes)}</span>
              </span>
            </button>`,
          )
          .join('')
      : '<div class="c4-empty">No full-text matches found.</div>';
  } else {
    const listItemsHtml = state.results.length
      ? state.results
          .map(
            (entry) => `
            <button class="c4-result-row" data-select-result="${escapeHtml(entry.name)}" aria-current="${entry.name === state.selectedName}">
              <span class="c4-result-name">${escapeHtml(entry.name)}</span>
              ${entry.source_url ? `<span class="c4-list-item-sub">${escapeHtml(entry.source_url)}</span>` : ''}
              <span class="c4-result-meta">
                <span>${formatBytes(entry.size_bytes)}</span>
                <span>${escapeHtml(formatDate(entry.modified))}</span>
              </span>
            </button>`,
          )
          .join('')
      : `<div class="c4-empty">${state.searchQuery.trim() ? 'No results match your filter.' : 'No saved crawls yet. Use "New Crawl" to capture a site.'}</div>`;

    const loadMoreHtml = state.hasMore
      ? `<div style="padding:8px 0 2px; text-align:center">
          <button class="c4-btn c4-btn--sm" data-action="load-more" ${state.loadingMore ? 'disabled' : ''}>
            ${state.loadingMore ? 'Loading…' : `Load more (${state.results.length} / ${state.totalResults})`}
          </button>
        </div>`
      : '';
    listHtml = listItemsHtml + loadMoreHtml;
  }

  const selectedEntry = state.results.find((r) => r.name === state.selectedName) ?? null;
  let detailHtml = '<div class="c4-empty">Select a saved crawl result to inspect it.</div>';

  if (state.loadingDoc) {
    detailHtml = '<div class="c4-empty"><span class="c4-spinner"></span> Loading Markdown…</div>';
  } else if (state.docError) {
    detailHtml = `<div class="c4-error-banner">${escapeHtml(state.docError)}</div>`;
  } else if (state.selectedDoc) {
    const doc = state.selectedDoc;
    const page = activePageSection();
    const displayUrl = page?.url ?? selectedEntry?.source_url ?? state.docSections[0]?.url ?? null;
    const safeUrl = displayUrl && isSafeHttpUrl(displayUrl) ? displayUrl : null;
    const displayedMarkdown = page ? page.content : doc.content;

    const pageBarHtml =
      state.docSections.length > 1
        ? `<div class="c4-page-bar">
            <label for="page-select" style="font-size:11px; color:var(--color-text-secondary)">Pages (${state.docSections.length})</label>
            <select id="page-select" class="c4-select">
              <option value="-1" ${state.selectedPageIndex === -1 ? 'selected' : ''}>All pages (${state.docSections.length})</option>
              ${state.docSections
                .map(
                  (sec) =>
                    `<option value="${sec.index}" ${state.selectedPageIndex === sec.index ? 'selected' : ''}>${sec.index + 1}. ${escapeHtml(sec.title)}${sec.url ? ` — ${escapeHtml(sec.url)}` : ''}</option>`,
                )
                .join('')}
            </select>
          </div>`
        : '';

    const metaRowHtml =
      page && (page.depth || page.timestamp)
        ? `<div class="c4-meta-row">
            ${page.depth ? `<span>Depth: ${escapeHtml(page.depth)}</span>` : ''}
            ${page.timestamp ? `<span>Captured: ${escapeHtml(formatDate(page.timestamp))}</span>` : ''}
          </div>`
        : '';

    detailHtml = `
      <div class="c4-header">
        <div style="min-width:0; flex:1">
          <div class="c4-title">${escapeHtml(page ? page.title : doc.name)}</div>
          ${
            safeUrl && canOpenLinks
              ? `<a class="c4-url" href="${escapeHtml(safeUrl)}" data-external-link="${escapeHtml(safeUrl)}">${escapeHtml(displayUrl!)}</a>`
              : displayUrl
                ? `<span class="c4-url">${escapeHtml(displayUrl)}</span>`
                : ''
          }
          ${metaRowHtml}
        </div>
        <span class="c4-badge">${formatBytes(page ? new TextEncoder().encode(page.rawSection).length : doc.size_bytes)}</span>
      </div>
      ${pageBarHtml}
      <div class="c4-toolbar">
        <div class="c4-actions">
          <button class="c4-btn c4-btn--sm" data-action="doc-rendered" ${state.renderMode === 'rendered' ? 'disabled' : ''}>Rendered</button>
          <button class="c4-btn c4-btn--sm" data-action="doc-raw" ${state.renderMode === 'raw' ? 'disabled' : ''}>Raw</button>
          <button class="c4-btn c4-btn--sm" data-action="doc-copy">${page ? 'Copy page' : 'Copy'}</button>
          ${
            canUpdateContext
              ? `<button class="c4-btn c4-btn--sm" data-action="doc-attach">${page ? 'Attach this page' : 'Attach to chat'}</button>`
              : ''
          }
          ${
            canMessage
              ? '<button class="c4-btn c4-btn--sm c4-btn--primary" data-action="doc-summarize">Summarize in chat</button>'
              : ''
          }
          ${safeUrl ? `<button class="c4-btn c4-btn--sm" data-recrawl-url="${escapeHtml(safeUrl)}">Re-crawl</button>` : ''}
          ${doc.file_uri ? '<button class="c4-btn c4-btn--sm" data-action="doc-open-file">Open .md</button>' : ''}
        </div>
      </div>
      <div class="c4-pane-scroll">
        ${
          state.renderMode === 'rendered'
            ? `<div class="c4-markdown">${renderSafeMarkdown(displayedMarkdown)}</div>`
            : `<pre class="c4-raw">${escapeHtml(displayedMarkdown)}</pre>`
        }
      </div>`;
  }

  return `
    <div class="c4-split">
      <section class="c4-pane">
        <div class="c4-search-bar">
          <input id="results-search" class="c4-input" type="search" placeholder="${state.searchMode === 'fulltext' ? 'Full-text search inside files…' : 'Filter by filename or URL…'}" value="${escapeHtml(state.searchQuery)}" />
        </div>
        <div class="c4-actions">
          <button class="c4-btn c4-btn--sm ${state.searchMode === 'meta' ? 'c4-btn--primary' : ''}" data-search-mode="meta">Name / URL</button>
          <button class="c4-btn c4-btn--sm ${state.searchMode === 'fulltext' ? 'c4-btn--primary' : ''}" data-search-mode="fulltext">Full text</button>
        </div>
        <div class="c4-pane-scroll">${listHtml}</div>
      </section>
      <section class="c4-pane">
        ${detailHtml}
      </section>
    </div>`;
}

function renderCrawlTab(): string {
  const isDeep = state.crawlMode === 'crawl';
  const result = state.lastCrawlResult;
  return `
    <div class="c4-pane" style="overflow:auto">
      <form id="crawl-form" class="c4-form">
        <div class="c4-actions">
          <button type="button" class="c4-btn c4-btn--sm ${!isDeep ? 'c4-btn--primary' : ''}" data-crawl-mode="crawl_page">Single page (fast)</button>
          <button type="button" class="c4-btn c4-btn--sm ${isDeep ? 'c4-btn--primary' : ''}" data-crawl-mode="crawl">Multi-page crawl (saved)</button>
        </div>

        <div class="c4-field">
          <label for="f-url">URL</label>
          <input id="f-url" class="c4-input" type="url" placeholder="https://docs.example.com/" value="${escapeHtml(state.formUrl)}" required />
        </div>

        <div class="c4-form-grid">
          <div class="c4-field">
            <label for="f-css">CSS selector (optional)</label>
            <input id="f-css" class="c4-input" type="text" placeholder="main, article" value="${escapeHtml(state.formCssSelector)}" />
          </div>
          <div class="c4-field">
            <label for="f-wait">Wait for selector (optional)</label>
            <input id="f-wait" class="c4-input" type="text" placeholder=".content-loaded" value="${escapeHtml(state.formWaitFor)}" />
          </div>
        </div>

        ${
          isDeep
            ? `<div class="c4-form-grid">
                <div class="c4-field">
                  <label for="f-depth">Max depth (0–5)</label>
                  <input id="f-depth" class="c4-input" type="number" min="0" max="5" value="${state.formMaxDepth}" />
                </div>
                <div class="c4-field">
                  <label for="f-pages">Max pages (1–500)</label>
                  <input id="f-pages" class="c4-input" type="number" min="1" max="500" value="${state.formMaxPages}" />
                </div>
                <div class="c4-field">
                  <label for="f-output">Output filename (optional)</label>
                  <input id="f-output" class="c4-input" type="text" placeholder="my_docs.md" value="${escapeHtml(state.formOutputFile)}" />
                </div>
              </div>
              <div class="c4-form-grid">
                <div class="c4-field">
                  <label for="f-include">Include URL patterns (comma-separated)</label>
                  <input id="f-include" class="c4-input" type="text" placeholder="/docs/*, */api/*" value="${escapeHtml(state.formIncludePatterns)}" />
                </div>
                <div class="c4-field">
                  <label for="f-exclude">Exclude URL patterns (comma-separated)</label>
                  <input id="f-exclude" class="c4-input" type="text" placeholder="/blog/*, *.pdf" value="${escapeHtml(state.formExcludePatterns)}" />
                </div>
              </div>`
            : ''
        }

        <div class="c4-checkbox-row">
          <label class="c4-checkbox">
            <input id="f-magic" type="checkbox" ${state.formMagic ? 'checked' : ''} />
            Magic mode (anti-bot heuristics)
          </label>
          ${
            isDeep
              ? `<label class="c4-checkbox">
                  <input id="f-external" type="checkbox" ${state.formIncludeExternal ? 'checked' : ''} />
                  Include external links
                </label>
                <label class="c4-checkbox">
                  <input id="f-overwrite" type="checkbox" ${state.formOverwrite ? 'checked' : ''} />
                  Overwrite existing file
                </label>`
              : ''
          }
        </div>

        <div class="c4-actions">
          <button type="submit" class="c4-btn c4-btn--primary" ${state.crawling ? 'disabled' : ''}>
            ${state.crawling ? '<span class="c4-spinner"></span> Crawling…' : isDeep ? 'Start Crawl' : 'Fetch Page'}
          </button>
        </div>
      </form>

      ${state.crawlError ? `<div class="c4-error-banner">${escapeHtml(state.crawlError)}</div>` : ''}

      ${
        result
          ? `<div class="c4-panel" style="margin-top:8px">
              <div class="c4-header">
                <strong>${escapeHtml(result.url)}</strong>
                <div class="c4-actions">
                  <span class="c4-badge c4-badge--success">${result.stats.successful_pages} OK · ${result.stats.duration_seconds.toFixed(1)}s</span>
                  ${
                    result.result_name
                      ? `<button class="c4-btn c4-btn--sm" data-open-saved="${escapeHtml(result.result_name)}">View in Saved Results</button>`
                      : ''
                  }
                </div>
              </div>
              <div class="c4-markdown" style="margin-top:8px">${renderSafeMarkdown(result.preview)}</div>
            </div>`
          : ''
      }
    </div>`;
}

function renderSessionsTab(): string {
  return `
    <div class="c4-pane">
      <div class="c4-header">
        <strong>Active Browser Sessions</strong>
        <span class="c4-badge">${state.sessions.length} active</span>
      </div>
      <div class="c4-pane-scroll">
        ${
          state.sessions.length
            ? `<ul class="c4-list">${state.sessions
                .map(
                  (sid) => `<li class="c4-list-item">
                    <div class="c4-list-item-main">
                      <span class="c4-list-item-url">${escapeHtml(sid)}</span>
                      <span class="c4-list-item-sub">Shared Chromium session (cookies &amp; page state)</span>
                    </div>
                    <button class="c4-btn c4-btn--sm" data-close-session="${escapeHtml(sid)}">Close session</button>
                  </li>`,
                )
                .join('')}</ul>`
            : '<div class="c4-empty">No open browser sessions. Pass a <code>session_id</code> to reuse cookies across crawls.</div>'
        }
      </div>
    </div>`;
}

function render(): void {
  const caps = app.getHostCapabilities();
  const canMessage = Boolean(caps?.message);
  const canUpdateContext = Boolean(caps?.updateModelContext);
  const canOpenLinks = Boolean(caps?.openLinks);

  let bodyHtml = '';
  if (state.activeTab === 'results') {
    bodyHtml = renderResultsTab(canMessage, canUpdateContext, canOpenLinks);
  } else if (state.activeTab === 'crawl') {
    bodyHtml = renderCrawlTab();
  } else {
    bodyHtml = renderSessionsTab();
  }

  root.innerHTML = `
    <header class="c4-header">
      <div class="c4-title-group">
        <span class="c4-brand-mark">&lt;&gt;</span>
        <h1 class="c4-title">Crawl4AI Explorer</h1>
      </div>
      <div class="c4-actions">
        <span id="explorer-toast" class="c4-toast">${escapeHtml(state.statusNote)}</span>
        <button class="c4-btn c4-btn--sm" data-action="refresh" ${state.loadingList ? 'disabled' : ''}>
          ${state.loadingList ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
    </header>

    <nav class="c4-tabs" role="tablist">
      <button class="c4-tab" role="tab" aria-selected="${state.activeTab === 'results'}" data-tab="results">
        Saved Results <span class="c4-tab-count">${state.totalAll || state.totalResults}</span>
      </button>
      <button class="c4-tab" role="tab" aria-selected="${state.activeTab === 'crawl'}" data-tab="crawl">
        New Crawl
      </button>
      <button class="c4-tab" role="tab" aria-selected="${state.activeTab === 'sessions'}" data-tab="sessions">
        Sessions <span class="c4-tab-count">${state.sessions.length}</span>
      </button>
    </nav>

    <div class="c4-explorer-body">
      ${bodyHtml}
    </div>
  `;

  const search = document.getElementById('results-search') as HTMLInputElement | null;
  if (search) {
    search.addEventListener('input', () => {
      state.searchQuery = search.value;
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        void refreshListing(undefined, true);
      }, 220);
    });
  }

  const pageSelect = document.getElementById('page-select') as HTMLSelectElement | null;
  if (pageSelect) {
    pageSelect.addEventListener('change', () => {
      state.selectedPageIndex = Number(pageSelect.value);
      render();
    });
  }

  const form = document.getElementById('crawl-form') as HTMLFormElement | null;
  if (form) {
    const syncForm = () => {
      state.formUrl = (document.getElementById('f-url') as HTMLInputElement | null)?.value ?? '';
      state.formCssSelector = (document.getElementById('f-css') as HTMLInputElement | null)?.value ?? '';
      state.formWaitFor = (document.getElementById('f-wait') as HTMLInputElement | null)?.value ?? '';
      state.formMagic = Boolean((document.getElementById('f-magic') as HTMLInputElement | null)?.checked);
      const depthEl = document.getElementById('f-depth') as HTMLInputElement | null;
      if (depthEl) state.formMaxDepth = Number(depthEl.value) || 0;
      const pagesEl = document.getElementById('f-pages') as HTMLInputElement | null;
      if (pagesEl) state.formMaxPages = Number(pagesEl.value) || 1;
      const outEl = document.getElementById('f-output') as HTMLInputElement | null;
      if (outEl) state.formOutputFile = outEl.value;
      const incEl = document.getElementById('f-include') as HTMLInputElement | null;
      if (incEl) state.formIncludePatterns = incEl.value;
      const excEl = document.getElementById('f-exclude') as HTMLInputElement | null;
      if (excEl) state.formExcludePatterns = excEl.value;
      const extEl = document.getElementById('f-external') as HTMLInputElement | null;
      if (extEl) state.formIncludeExternal = extEl.checked;
      const ovEl = document.getElementById('f-overwrite') as HTMLInputElement | null;
      if (ovEl) state.formOverwrite = ovEl.checked;
    };
    form.addEventListener('input', syncForm);
    form.addEventListener('change', syncForm);
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      syncForm();
      void runCrawlFromForm();
    });
  }
}

root.addEventListener('click', (event) => {
  const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
    '[data-tab], [data-action], [data-select-result], [data-crawl-mode], [data-close-session], [data-open-saved], [data-search-mode], [data-recrawl-url]',
  );
  if (!target) return;

  if (target.dataset.tab) {
    state.activeTab = target.dataset.tab as ExplorerState['activeTab'];
    render();
    return;
  }

  if (target.dataset.searchMode) {
    const nextMode = target.dataset.searchMode as ExplorerState['searchMode'];
    if (nextMode !== state.searchMode) {
      state.searchMode = nextMode;
      render();
      void refreshListing(undefined, true);
    }
    return;
  }

  if (target.dataset.selectResult) {
    void loadDocument(target.dataset.selectResult);
    return;
  }

  if (target.dataset.crawlMode) {
    state.crawlMode = target.dataset.crawlMode as ExplorerState['crawlMode'];
    render();
    return;
  }

  if (target.dataset.closeSession) {
    void closeSession(target.dataset.closeSession);
    return;
  }

  if (target.dataset.openSaved) {
    state.activeTab = 'results';
    void loadDocument(target.dataset.openSaved);
    return;
  }

  if (target.dataset.recrawlUrl) {
    state.formUrl = target.dataset.recrawlUrl;
    state.crawlMode = 'crawl_page';
    state.activeTab = 'crawl';
    render();
    return;
  }

  const action = target.dataset.action;
  if (action === 'refresh') {
    void refreshListing();
  } else if (action === 'load-more') {
    void loadMoreResults();
  } else if (action === 'doc-rendered') {
    state.renderMode = 'rendered';
    render();
  } else if (action === 'doc-raw') {
    state.renderMode = 'raw';
    render();
  } else if (action === 'doc-copy' && state.selectedDoc) {
    const page = activePageSection();
    const text = page ? page.rawSection : state.selectedDoc.content;
    void copyToClipboard(text).then((ok) => flashStatus(ok ? 'Copied!' : 'Clipboard unavailable'));
  } else if (action === 'doc-attach' && state.selectedDoc) {
    const doc = state.selectedDoc;
    const page = activePageSection();
    const content = page
      ? [
          {
            type: 'text' as const,
            text: `Page "${page.title}"${page.url ? ` (${page.url})` : ''} from ${doc.name}:\n\n${page.rawSection}`,
          },
        ]
      : [
          {
            type: 'resource_link' as const,
            uri: doc.uri,
            name: doc.name,
            mimeType: 'text/markdown',
          },
          {
            type: 'text' as const,
            text: `Saved crawl result "${doc.name}" (${formatBytes(doc.size_bytes)}).`,
          },
        ];
    void app
      .updateModelContext({ content })
      .then(() => flashStatus(page ? 'Page attached to next message' : 'Attached to next message'))
      .catch(() => flashStatus('Attach unavailable'));
  } else if (action === 'doc-summarize' && state.selectedDoc) {
    const doc = state.selectedDoc;
    const page = activePageSection();
    const prompt = page
      ? `Summarize the page "${page.title}" (${page.url ?? doc.name}) from ${doc.uri}.`
      : `Read the crawl result resource ${doc.uri} and summarize its main sections and key takeaways.`;
    void app
      .sendMessage({
        role: 'user',
        content: [{ type: 'text', text: prompt }],
      })
      .then((res) => flashStatus(res.isError ? 'Message rejected' : 'Sent to chat'))
      .catch(() => flashStatus('Message unavailable'));
  } else if (action === 'doc-open-file' && state.selectedDoc?.file_uri) {
    void openFileInAuxPane(app, state.selectedDoc.file_uri).then((ok) => {
      if (!ok) flashStatus('Side pane file view unavailable');
    });
  }
});

wireExternalLinks(root, app);

// Register handlers BEFORE connect() so no notification is missed.
app.ontoolresult = (result) => {
  if (result.isError) return;
  const payload = result.structuredContent as ExplorerPayload | undefined;
  if (!payload || payload.kind !== 'explorer') return;

  state.results = payload.results ?? [];
  state.totalResults = payload.total_results ?? state.results.length;
  state.totalAll = state.totalResults;
  state.hasMore = Boolean(payload.has_more);
  state.sessions = payload.sessions ?? [];

  if (payload.initial_url) {
    state.formUrl = payload.initial_url;
    state.activeTab = 'crawl';
  }
  if (payload.selected_result) {
    state.activeTab = 'results';
    state.selectedName = payload.selected_result;
  } else if (!state.selectedName && state.results.length > 0) {
    state.selectedName = state.results[0].name;
  }

  render();
  if (state.activeTab === 'results' && state.selectedName) {
    void loadDocument(state.selectedName);
  }
};

app.onhostcontextchanged = (ctx) => {
  applyThemeFromContext(ctx);
};

async function init(): Promise<void> {
  render();
  await app.connect();
  state.connected = true;
  applyThemeFromContext(app.getHostContext());
  render();
}

void init();
