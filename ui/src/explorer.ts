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
  renderSafeMarkdown,
  wireExternalLinks,
  type CrawlCardPayload,
  type ExplorerPayload,
  type ListResultsPayload,
  type ReadResultPayload,
  type SavedResultEntry,
} from './shared';

const root = document.getElementById('root')!;
const PAGE_SIZE = 200;

interface ExplorerState {
  connected: boolean;
  activeTab: 'results' | 'crawl' | 'sessions';
  results: SavedResultEntry[];
  totalResults: number;
  totalAll: number;
  hasMore: boolean;
  loadingMore: boolean;
  sessions: string[];
  searchQuery: string;
  selectedName: string | null;
  selectedDoc: ReadResultPayload | null;
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
  totalResults: 0,
  totalAll: 0,
  hasMore: false,
  loadingMore: false,
  sessions: [],
  searchQuery: '',
  selectedName: null,
  selectedDoc: null,
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

async function refreshListing(selectName?: string, preserveFocus = false): Promise<void> {
  const seq = ++listRequestSeq;
  state.loadingList = true;
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
      } else if (!state.selectedName || (!state.searchQuery.trim() && !state.results.some((r) => r.name === state.selectedName))) {
        state.selectedName = state.results[0]?.name ?? null;
      }
    }
  } catch {
    if (seq === listRequestSeq) flashStatus('Failed to refresh');
  } finally {
    if (seq !== listRequestSeq) return;
    state.loadingList = false;
    render();
    if (preserveFocus) {
      const refocused = document.getElementById('results-search') as HTMLInputElement | null;
      if (refocused) {
        refocused.focus();
        refocused.setSelectionRange(refocused.value.length, refocused.value.length);
      }
    }
    if (!preserveFocus && state.selectedName) {
      void loadDocument(state.selectedName);
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
  state.selectedName = name;
  state.loadingDoc = true;
  state.docError = null;
  render();
  try {
    const res = await app.callServerTool({
      name: 'app_read_result',
      arguments: { name },
    });
    if (res.isError) {
      state.selectedDoc = null;
      state.docError = extractErrorMessage(res);
    } else {
      const data = res.structuredContent as ReadResultPayload | undefined;
      state.selectedDoc = data ?? null;
      if (!data) state.docError = 'Empty result payload.';
    }
  } catch (err) {
    state.selectedDoc = null;
    state.docError = err instanceof Error ? err.message : 'Failed to read result.';
  } finally {
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

function renderResultsTab(canMessage: boolean, canUpdateContext: boolean, canOpenLinks: boolean): string {
  const filtered = state.results;

  const listItemsHtml = filtered.length
    ? filtered
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
          ${state.loadingMore ? 'Loading…' : `Load more (${filtered.length} / ${state.totalResults})`}
        </button>
      </div>`
    : '';

  const listHtml = listItemsHtml + loadMoreHtml;

  const selectedEntry = state.results.find((r) => r.name === state.selectedName) ?? null;
  let detailHtml = '<div class="c4-empty">Select a saved crawl result to inspect it.</div>';

  if (state.loadingDoc) {
    detailHtml = '<div class="c4-empty"><span class="c4-spinner"></span> Loading Markdown…</div>';
  } else if (state.docError) {
    detailHtml = `<div class="c4-error-banner">${escapeHtml(state.docError)}</div>`;
  } else if (state.selectedDoc) {
    const doc = state.selectedDoc;
    const sourceUrl = selectedEntry?.source_url ?? null;
    const safeUrl = sourceUrl && isSafeHttpUrl(sourceUrl) ? sourceUrl : null;
    detailHtml = `
      <div class="c4-header">
        <div style="min-width:0; flex:1">
          <div class="c4-title">${escapeHtml(doc.name)}</div>
          ${
            safeUrl && canOpenLinks
              ? `<a class="c4-url" href="${escapeHtml(safeUrl)}" data-external-link="${escapeHtml(safeUrl)}">${escapeHtml(sourceUrl!)}</a>`
              : sourceUrl
                ? `<span class="c4-url">${escapeHtml(sourceUrl)}</span>`
                : ''
          }
        </div>
        <span class="c4-badge">${formatBytes(doc.size_bytes)}</span>
      </div>
      <div class="c4-toolbar">
        <div class="c4-actions">
          <button class="c4-btn c4-btn--sm" data-action="doc-rendered" ${state.renderMode === 'rendered' ? 'disabled' : ''}>Rendered</button>
          <button class="c4-btn c4-btn--sm" data-action="doc-raw" ${state.renderMode === 'raw' ? 'disabled' : ''}>Raw</button>
          <button class="c4-btn c4-btn--sm" data-action="doc-copy">Copy</button>
          ${canUpdateContext ? '<button class="c4-btn c4-btn--sm" data-action="doc-attach">Attach to chat</button>' : ''}
          ${canMessage ? '<button class="c4-btn c4-btn--sm c4-btn--primary" data-action="doc-summarize">Summarize in chat</button>' : ''}
          ${doc.file_uri ? '<button class="c4-btn c4-btn--sm" data-action="doc-open-file">Open .md</button>' : ''}
        </div>
      </div>
      <div class="c4-pane-scroll">
        ${
          state.renderMode === 'rendered'
            ? `<div class="c4-markdown">${renderSafeMarkdown(doc.content)}</div>`
            : `<pre class="c4-raw">${escapeHtml(doc.content)}</pre>`
        }
      </div>`;
  }

  return `
    <div class="c4-split">
      <section class="c4-pane">
        <input id="results-search" class="c4-input" type="search" placeholder="Search saved crawls…" value="${escapeHtml(state.searchQuery)}" />
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
      }, 200);
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
    '[data-tab], [data-action], [data-select-result], [data-crawl-mode], [data-close-session], [data-open-saved]',
  );
  if (!target) return;

  if (target.dataset.tab) {
    state.activeTab = target.dataset.tab as ExplorerState['activeTab'];
    render();
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
    void copyToClipboard(state.selectedDoc.content).then((ok) =>
      flashStatus(ok ? 'Copied!' : 'Clipboard unavailable'),
    );
  } else if (action === 'doc-attach' && state.selectedDoc) {
    const doc = state.selectedDoc;
    void app
      .updateModelContext({
        content: [
          {
            type: 'resource_link',
            uri: doc.uri,
            name: doc.name,
            mimeType: 'text/markdown',
          },
          {
            type: 'text',
            text: `Saved crawl result "${doc.name}" (${formatBytes(doc.size_bytes)}).`,
          },
        ],
      })
      .then(() => flashStatus('Attached to next message'))
      .catch(() => flashStatus('Attach unavailable'));
  } else if (action === 'doc-summarize' && state.selectedDoc) {
    const doc = state.selectedDoc;
    void app
      .sendMessage({
        role: 'user',
        content: [
          {
            type: 'text',
            text: `Read the crawl result resource ${doc.uri} and summarize its main sections and key takeaways.`,
          },
        ],
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
