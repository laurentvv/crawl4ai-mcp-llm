import { App } from '@modelcontextprotocol/ext-apps';
import './styles.css';
import {
  applyThemeFromContext,
  copyToClipboard,
  escapeHtml,
  extractErrorMessage,
  isSafeHttpUrl,
  openFileInAuxPane,
  renderSafeMarkdown,
  wireExternalLinks,
  type CrawlCardPayload,
  type ReadResultPayload,
} from './shared';

const root = document.getElementById('root')!;

interface CardState {
  phase: 'idle' | 'loading' | 'ready' | 'cancelled' | 'error';
  inputArgs?: Record<string, unknown>;
  payload?: CrawlCardPayload;
  fullMarkdown?: string;
  loadingFull: boolean;
  activeTab: 'content' | 'links' | 'skipped';
  renderMode: 'rendered' | 'raw';
  linkScope: 'all' | 'internal' | 'external';
  linkQuery: string;
  statusNote: string;
  errorMessage?: string;
}

const state: CardState = {
  phase: 'idle',
  loadingFull: false,
  activeTab: 'content',
  renderMode: 'rendered',
  linkScope: 'all',
  linkQuery: '',
  statusNote: '',
};

const app = new App({ name: 'Crawl4AI Result Card', version: '1.0.0' }, {});

function flashStatus(message: string): void {
  state.statusNote = message;
  const el = document.getElementById('status-note');
  if (el) el.textContent = message;
  window.setTimeout(() => {
    if (state.statusNote === message) {
      state.statusNote = '';
      const current = document.getElementById('status-note');
      if (current) current.textContent = '';
    }
  }, 2600);
}

function render(): void {
  const caps = app.getHostCapabilities();
  const canMessage = Boolean(caps?.message);
  const canUpdateContext = Boolean(caps?.updateModelContext);
  const canOpenLinks = Boolean(caps?.openLinks);

  if (state.phase === 'idle') {
    root.innerHTML = `
      <div class="c4-header">
        <div class="c4-title-group">
          <span class="c4-brand-mark">&lt;&gt;</span>
          <span class="c4-spinner" aria-hidden="true"></span>
          <h1 class="c4-title">Connecting to Crawl4AI…</h1>
        </div>
      </div>`;
    return;
  }

  if (state.phase === 'loading') {
    const url = typeof state.inputArgs?.url === 'string' ? state.inputArgs.url : '';
    const depth = state.inputArgs?.max_depth;
    const pages = state.inputArgs?.max_pages;
    const selector = state.inputArgs?.css_selector;
    const badges: string[] = [];
    if (typeof depth === 'number') badges.push(`depth ${depth}`);
    if (typeof pages === 'number') badges.push(`max ${pages} pages`);
    if (typeof selector === 'string' && selector) badges.push(`css: ${selector}`);
    if (state.inputArgs?.magic) badges.push('magic');

    root.innerHTML = `
      <div class="c4-header">
        <div class="c4-title-group">
          <span class="c4-brand-mark">&lt;&gt;</span>
          <span class="c4-spinner" aria-hidden="true"></span>
          <div style="min-width:0">
            <h1 class="c4-title">Crawling web content…</h1>
            ${url ? `<span class="c4-url">${escapeHtml(url)}</span>` : ''}
          </div>
        </div>
        <div class="c4-actions">
          ${badges.map((b) => `<span class="c4-badge">${escapeHtml(b)}</span>`).join('')}
        </div>
      </div>`;
    return;
  }

  if (state.phase === 'cancelled') {
    root.innerHTML = `
      <div class="c4-header">
        <div class="c4-title-group">
          <span class="c4-brand-mark">&lt;&gt;</span>
          <h1 class="c4-title">Crawl cancelled</h1>
        </div>
        <span class="c4-badge c4-badge--warning">Cancelled</span>
      </div>`;
    return;
  }

  if (state.phase === 'error' || !state.payload) {
    root.innerHTML = `
      <div class="c4-header">
        <div class="c4-title-group">
          <span class="c4-brand-mark">&lt;&gt;</span>
          <h1 class="c4-title">Crawl failed</h1>
        </div>
        <span class="c4-badge c4-badge--danger">Error</span>
      </div>
      <div class="c4-error-banner">${escapeHtml(state.errorMessage ?? 'No crawl result available.')}</div>`;
    return;
  }

  const p = state.payload;
  const badgeClass =
    p.status === 'completed'
      ? 'c4-badge--success'
      : p.status === 'partial'
        ? 'c4-badge--warning'
        : 'c4-badge--danger';
  const badgeLabel =
    p.kind === 'crawl_page'
      ? 'Page fetched'
      : p.status === 'completed'
        ? 'Completed'
        : p.status === 'partial'
          ? 'Partial (timeout)'
          : 'No usable pages';

  const currentMarkdown = state.fullMarkdown ?? p.preview ?? '';
  const totalLinks = p.links.total_internal + p.links.total_external;
  const safeUrl = isSafeHttpUrl(p.url) ? p.url : null;

  const headerUrl =
    safeUrl && canOpenLinks
      ? `<a class="c4-url" href="${escapeHtml(safeUrl)}" data-external-link="${escapeHtml(safeUrl)}">${escapeHtml(p.url)}</a>`
      : `<span class="c4-url">${escapeHtml(p.url)}</span>`;

  const kpis =
    p.kind === 'crawl'
      ? `
      <div class="c4-kpis">
        <div class="c4-kpi"><span class="c4-kpi-label">Pages OK</span><span class="c4-kpi-value">${p.stats.successful_pages}</span></div>
        <div class="c4-kpi"><span class="c4-kpi-label">Failed</span><span class="c4-kpi-value">${p.stats.failed_pages}</span></div>
        <div class="c4-kpi"><span class="c4-kpi-label">404 / 403</span><span class="c4-kpi-value">${p.stats.not_found_pages} / ${p.stats.forbidden_pages}</span></div>
        <div class="c4-kpi"><span class="c4-kpi-label">Duration</span><span class="c4-kpi-value">${p.stats.duration_seconds.toFixed(1)}s</span></div>
        <div class="c4-kpi"><span class="c4-kpi-label">Links</span><span class="c4-kpi-value">${totalLinks}</span></div>
      </div>`
      : '';

  let tabBody = '';
  if (state.activeTab === 'content') {
    const isTruncated = !state.fullMarkdown && (p.preview_truncated || p.content_truncated);
    tabBody = `
      <div class="c4-toolbar">
        <div class="c4-actions">
          <button class="c4-btn c4-btn--sm" data-action="mode-rendered" ${state.renderMode === 'rendered' ? 'disabled' : ''}>Rendered</button>
          <button class="c4-btn c4-btn--sm" data-action="mode-raw" ${state.renderMode === 'raw' ? 'disabled' : ''}>Raw Markdown</button>
          ${
            isTruncated && p.result_name
              ? `<button class="c4-btn c4-btn--sm c4-btn--primary" data-action="load-full" ${state.loadingFull ? 'disabled' : ''}>${state.loadingFull ? 'Loading…' : 'Load full Markdown'}</button>`
              : ''
          }
        </div>
        ${isTruncated ? `<span class="c4-badge c4-badge--info">Preview truncated</span>` : ''}
      </div>
      <div class="c4-panel c4-panel--scroll">
        ${
          currentMarkdown
            ? state.renderMode === 'rendered'
              ? `<div class="c4-markdown">${renderSafeMarkdown(currentMarkdown)}</div>`
              : `<pre class="c4-raw">${escapeHtml(currentMarkdown)}</pre>`
            : '<div class="c4-empty">No content extracted.</div>'
        }
      </div>`;
  } else if (state.activeTab === 'links') {
    const query = state.linkQuery.trim().toLowerCase();
    const items: Array<{ kind: 'internal' | 'external'; href: string; text?: string }> = [];
    if (state.linkScope !== 'external') {
      for (const l of p.links.internal) items.push({ kind: 'internal', ...l });
    }
    if (state.linkScope !== 'internal') {
      for (const l of p.links.external) items.push({ kind: 'external', ...l });
    }
    const filtered = query
      ? items.filter(
          (i) => i.href.toLowerCase().includes(query) || (i.text ?? '').toLowerCase().includes(query),
        )
      : items;

    tabBody = `
      <div class="c4-toolbar">
        <div class="c4-actions">
          <button class="c4-btn c4-btn--sm" data-link-scope="all" ${state.linkScope === 'all' ? 'disabled' : ''}>All (${totalLinks})</button>
          <button class="c4-btn c4-btn--sm" data-link-scope="internal" ${state.linkScope === 'internal' ? 'disabled' : ''}>Internal (${p.links.total_internal})</button>
          <button class="c4-btn c4-btn--sm" data-link-scope="external" ${state.linkScope === 'external' ? 'disabled' : ''}>External (${p.links.total_external})</button>
        </div>
        <input id="link-search" class="c4-input" type="search" placeholder="Filter links…" value="${escapeHtml(state.linkQuery)}" />
      </div>
      <div class="c4-panel c4-panel--scroll">
        ${
          filtered.length
            ? `<ul class="c4-list">${filtered
                .map((item) => {
                  const safeHref = isSafeHttpUrl(item.href) ? item.href : null;
                  return `<li class="c4-list-item">
                    <div class="c4-list-item-main">
                      ${
                        safeHref && canOpenLinks
                          ? `<a class="c4-list-item-url" href="${escapeHtml(safeHref)}" data-external-link="${escapeHtml(safeHref)}">${escapeHtml(item.href)}</a>`
                          : `<span class="c4-list-item-url">${escapeHtml(item.href)}</span>`
                      }
                      <span class="c4-list-item-sub">${item.kind}${item.text ? ` · ${escapeHtml(item.text)}` : ''}</span>
                    </div>
                    ${
                      safeHref && canMessage
                        ? `<button class="c4-btn c4-btn--sm" data-crawl-url="${escapeHtml(safeHref)}">Crawl</button>`
                        : ''
                    }
                  </li>`;
                })
                .join('')}</ul>`
            : '<div class="c4-empty">No matching links.</div>'
        }
      </div>`;
  } else {
    tabBody = `
      <div class="c4-panel c4-panel--scroll">
        ${
          p.skipped.length
            ? `<ul class="c4-list">${p.skipped
                .map(
                  (s) => `<li class="c4-list-item">
                    <div class="c4-list-item-main">
                      <span class="c4-list-item-url">${escapeHtml(s.url)}</span>
                      <span class="c4-list-item-sub">${escapeHtml(s.reason)}</span>
                    </div>
                  </li>`,
                )
                .join('')}</ul>`
            : '<div class="c4-empty">No skipped pages.</div>'
        }
      </div>`;
  }

  root.innerHTML = `
    <div class="c4-header">
      <div class="c4-title-group">
        <span class="c4-brand-mark">&lt;&gt;</span>
        <div style="min-width:0">
          <h1 class="c4-title">${p.kind === 'crawl_page' ? 'Page Snapshot' : 'Crawl Summary'}</h1>
          ${headerUrl}
        </div>
      </div>
      <div class="c4-actions">
        <span class="c4-badge ${badgeClass}">${badgeLabel}</span>
        ${p.kind === 'crawl_page' ? `<span class="c4-badge">${p.stats.duration_seconds.toFixed(1)}s</span>` : ''}
      </div>
    </div>

    ${kpis}

    <div class="c4-actions">
      <button class="c4-btn c4-btn--sm" data-action="copy">Copy Markdown</button>
      ${
        canUpdateContext
          ? `<button class="c4-btn c4-btn--sm" data-action="attach">Attach to next message</button>`
          : ''
      }
      ${
        p.file_uri
          ? `<button class="c4-btn c4-btn--sm" data-action="open-file">Open .md file</button>`
          : ''
      }
      <span id="status-note" class="c4-toast">${escapeHtml(state.statusNote)}</span>
    </div>

    <div class="c4-tabs" role="tablist">
      <button class="c4-tab" role="tab" aria-selected="${state.activeTab === 'content'}" data-tab="content">Content</button>
      <button class="c4-tab" role="tab" aria-selected="${state.activeTab === 'links'}" data-tab="links">
        Links <span class="c4-tab-count">${totalLinks}</span>
      </button>
      ${
        p.kind === 'crawl'
          ? `<button class="c4-tab" role="tab" aria-selected="${state.activeTab === 'skipped'}" data-tab="skipped">
              Skipped <span class="c4-tab-count">${p.total_skipped}</span>
            </button>`
          : ''
      }
    </div>

    ${tabBody}
  `;

  const search = document.getElementById('link-search') as HTMLInputElement | null;
  if (search) {
    search.addEventListener('input', () => {
      state.linkQuery = search.value;
      render();
      const refocused = document.getElementById('link-search') as HTMLInputElement | null;
      if (refocused) {
        refocused.focus();
        refocused.setSelectionRange(refocused.value.length, refocused.value.length);
      }
    });
  }
}

root.addEventListener('click', (event) => {
  const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
    '[data-tab], [data-action], [data-link-scope], [data-crawl-url]',
  );
  if (!target) return;

  if (target.dataset.tab) {
    state.activeTab = target.dataset.tab as CardState['activeTab'];
    render();
    return;
  }

  if (target.dataset.linkScope) {
    state.linkScope = target.dataset.linkScope as CardState['linkScope'];
    render();
    return;
  }

  if (target.dataset.crawlUrl) {
    const url = target.dataset.crawlUrl;
    void app
      .sendMessage({
        role: 'user',
        content: [{ type: 'text', text: `Fetch ${url} with crawl_page and summarize the key points.` }],
      })
      .then((res) => {
        flashStatus(res.isError ? 'Message rejected by host' : 'Sent to chat');
      })
      .catch(() => flashStatus('Could not send message'));
    return;
  }

  const action = target.dataset.action;
  if (action === 'mode-rendered') {
    state.renderMode = 'rendered';
    render();
  } else if (action === 'mode-raw') {
    state.renderMode = 'raw';
    render();
  } else if (action === 'copy' && state.payload) {
    const text = state.fullMarkdown ?? state.payload.preview ?? '';
    void copyToClipboard(text).then((ok) => flashStatus(ok ? 'Copied!' : 'Clipboard unavailable'));
  } else if (action === 'attach' && state.payload) {
    const p = state.payload;
    const content = p.resource_uri
      ? [
          {
            type: 'resource_link' as const,
            uri: p.resource_uri,
            name: p.result_name ?? p.url,
            mimeType: 'text/markdown',
          },
          {
            type: 'text' as const,
            text: `Crawl result for ${p.url} (${p.stats.successful_pages} pages).`,
          },
        ]
      : [
          {
            type: 'text' as const,
            text: `Extracted content from ${p.url}:\n\n${state.fullMarkdown ?? p.preview}`,
          },
        ];
    void app
      .updateModelContext({ content })
      .then(() => flashStatus('Attached to next message'))
      .catch(() => flashStatus('Attach unavailable'));
  } else if (action === 'open-file' && state.payload?.file_uri) {
    void openFileInAuxPane(app, state.payload.file_uri).then((ok) => {
      if (!ok) flashStatus('Side pane file view unavailable');
    });
  } else if (action === 'load-full' && state.payload?.result_name) {
    state.loadingFull = true;
    render();
    void app
      .callServerTool({
        name: 'app_read_result',
        arguments: { name: state.payload.result_name },
      })
      .then((res) => {
        state.loadingFull = false;
        if (res.isError) {
          flashStatus(extractErrorMessage(res));
        } else {
          const data = res.structuredContent as ReadResultPayload | undefined;
          if (data?.content) {
            state.fullMarkdown = data.content;
            flashStatus('Loaded full Markdown');
          }
        }
        render();
      })
      .catch(() => {
        state.loadingFull = false;
        flashStatus('Failed to load full file');
        render();
      });
  }
});

wireExternalLinks(root, app);

// Register handlers BEFORE connect() so no notification is missed.
app.ontoolinput = (params) => {
  state.phase = 'loading';
  state.inputArgs = (params.arguments ?? {}) as Record<string, unknown>;
  render();
};

app.ontoolresult = (result) => {
  if (result.isError) {
    state.phase = 'error';
    state.errorMessage = extractErrorMessage(result);
    render();
    return;
  }
  const data = result.structuredContent as CrawlCardPayload | undefined;
  if (data && (data.kind === 'crawl' || data.kind === 'crawl_page')) {
    state.phase = 'ready';
    state.payload = data;
    state.fullMarkdown = undefined;
    render();
    return;
  }
  const fallbackText = extractErrorMessage(result);
  state.phase = 'ready';
  state.payload = {
    kind: 'crawl_page',
    status: 'completed',
    url: typeof state.inputArgs?.url === 'string' ? state.inputArgs.url : '',
    stats: {
      successful_pages: 1,
      failed_pages: 0,
      not_found_pages: 0,
      forbidden_pages: 0,
      duration_seconds: 0,
    },
    links: { internal: [], external: [], total_internal: 0, total_external: 0 },
    skipped: [],
    total_skipped: 0,
    preview: fallbackText,
    preview_truncated: false,
    content_truncated: false,
    timed_out: false,
  };
  render();
};

app.ontoolcancelled = () => {
  state.phase = 'cancelled';
  render();
};

app.onhostcontextchanged = (ctx) => {
  applyThemeFromContext(ctx);
};

async function init(): Promise<void> {
  render();
  await app.connect();
  applyThemeFromContext(app.getHostContext());
  render();
}

void init();
