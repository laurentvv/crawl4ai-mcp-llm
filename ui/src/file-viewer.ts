import { App } from '@modelcontextprotocol/ext-apps';
import './styles.css';
import {
  applyThemeFromContext,
  copyToClipboard,
  decodeBase64Utf8,
  escapeHtml,
  extractErrorMessage,
  formatBytes,
  formatDate,
  isSafeHttpUrl,
  parseCrawledDocument,
  renderSafeMarkdown,
  wireExternalLinks,
  type CrawlCardPayload,
  type CrawledPageSection,
  type FileViewerPayload,
} from './shared';

const root = document.getElementById('root')!;

interface ViewerState {
  fileName: string;
  resourceUri: string | null;
  loading: boolean;
  error: string | null;
  rawMarkdown: string;
  sections: CrawledPageSection[];
  selectedIndex: number;
  tocFilter: string;
  renderMode: 'rendered' | 'raw';
  recrawling: boolean;
  recrawlPreview: CrawlCardPayload | null;
  recrawlError: string | null;
  statusNote: string;
}

const state: ViewerState = {
  fileName: 'crawl.md',
  resourceUri: null,
  loading: true,
  error: null,
  rawMarkdown: '',
  sections: [],
  selectedIndex: 0,
  tocFilter: '',
  renderMode: 'rendered',
  recrawling: false,
  recrawlPreview: null,
  recrawlError: null,
  statusNote: '',
};

const app = new App({ name: 'Crawl4AI File Viewer', version: '1.0.0' }, {});

function flashStatus(message: string): void {
  state.statusNote = message;
  const el = document.getElementById('viewer-toast');
  if (el) el.textContent = message;
  window.setTimeout(() => {
    if (state.statusNote === message) {
      state.statusNote = '';
      const current = document.getElementById('viewer-toast');
      if (current) current.textContent = '';
    }
  }, 2600);
}

async function loadHostFile(fileName: string, resourceUri: string): Promise<void> {
  state.fileName = fileName;
  state.resourceUri = resourceUri;
  state.loading = true;
  state.error = null;
  state.recrawlPreview = null;
  state.recrawlError = null;
  render();

  try {
    const res = await app.readServerResource({ uri: resourceUri });
    const entry = res.contents?.[0];
    let text = '';
    if (entry && 'text' in entry && typeof entry.text === 'string') {
      text = entry.text;
    } else if (entry && 'blob' in entry && typeof entry.blob === 'string') {
      text = decodeBase64Utf8(entry.blob);
    } else {
      throw new Error('Host returned an empty file resource.');
    }
    state.rawMarkdown = text;
    state.sections = parseCrawledDocument(text);
    state.selectedIndex = 0;
  } catch (err) {
    state.error = err instanceof Error ? err.message : 'Failed to read file.';
  } finally {
    state.loading = false;
    render();
  }
}

async function recrawlCurrentUrl(url: string): Promise<void> {
  state.recrawling = true;
  state.recrawlError = null;
  state.recrawlPreview = null;
  render();
  try {
    const res = await app.callServerTool({
      name: 'crawl_page',
      arguments: { url },
    });
    if (res.isError) {
      state.recrawlError = extractErrorMessage(res);
    } else {
      state.recrawlPreview = (res.structuredContent as CrawlCardPayload | undefined) ?? null;
      flashStatus('Re-crawled live snapshot');
    }
  } catch (err) {
    state.recrawlError = err instanceof Error ? err.message : 'Re-crawl failed.';
  } finally {
    state.recrawling = false;
    render();
  }
}

function render(): void {
  const caps = app.getHostCapabilities();
  const canUpdateContext = Boolean(caps?.updateModelContext);
  const canOpenLinks = Boolean(caps?.openLinks);

  if (state.loading) {
    root.innerHTML = `
      <div class="c4-header">
        <div class="c4-title-group">
          <span class="c4-brand-mark">&lt;&gt;</span>
          <span class="c4-spinner" aria-hidden="true"></span>
          <h1 class="c4-title">Loading ${escapeHtml(state.fileName)}…</h1>
        </div>
      </div>`;
    return;
  }

  if (state.error) {
    root.innerHTML = `
      <div class="c4-header">
        <div class="c4-title-group">
          <span class="c4-brand-mark">&lt;&gt;</span>
          <h1 class="c4-title">${escapeHtml(state.fileName)}</h1>
        </div>
        <span class="c4-badge c4-badge--danger">Error</span>
      </div>
      <div class="c4-error-banner">${escapeHtml(state.error)}</div>`;
    return;
  }

  const query = state.tocFilter.trim().toLowerCase();
  const filteredSections = query
    ? state.sections.filter(
        (s) =>
          s.title.toLowerCase().includes(query) ||
          (s.url ?? '').toLowerCase().includes(query),
      )
    : state.sections;

  const current = state.sections[state.selectedIndex] ?? state.sections[0] ?? null;
  const safeUrl = current?.url && isSafeHttpUrl(current.url) ? current.url : null;
  const totalBytes = new TextEncoder().encode(state.rawMarkdown).length;

  const tocHtml = filteredSections.length
    ? filteredSections
        .map(
          (sec) => `
          <button class="c4-result-row" data-select-page="${sec.index}" aria-current="${sec.index === state.selectedIndex}">
            <span class="c4-result-name">${sec.index + 1}. ${escapeHtml(sec.title)}</span>
            ${sec.url ? `<span class="c4-list-item-sub">${escapeHtml(sec.url)}</span>` : ''}
            <span class="c4-result-meta">
              <span>${sec.depth ? `depth ${escapeHtml(sec.depth)}` : 'page'}</span>
              <span>${sec.timestamp ? escapeHtml(formatDate(sec.timestamp)) : ''}</span>
            </span>
          </button>`,
        )
        .join('')
    : '<div class="c4-empty">No matching pages in TOC.</div>';

  const bodyHtml = current
    ? `
      <div class="c4-header">
        <div style="min-width:0; flex:1">
          <div class="c4-title">${escapeHtml(current.title)}</div>
          ${
            safeUrl && canOpenLinks
              ? `<a class="c4-url" href="${escapeHtml(safeUrl)}" data-external-link="${escapeHtml(safeUrl)}">${escapeHtml(current.url!)}</a>`
              : current.url
                ? `<span class="c4-url">${escapeHtml(current.url)}</span>`
                : ''
          }
          <div class="c4-meta-row">
            ${current.depth ? `<span>Depth: ${escapeHtml(current.depth)}</span>` : ''}
            ${current.timestamp ? `<span>Captured: ${escapeHtml(formatDate(current.timestamp))}</span>` : ''}
          </div>
        </div>
        <span class="c4-badge">Page ${current.index + 1} / ${state.sections.length}</span>
      </div>
      <div class="c4-toolbar">
        <div class="c4-actions">
          <button class="c4-btn c4-btn--sm" data-action="mode-rendered" ${state.renderMode === 'rendered' ? 'disabled' : ''}>Rendered</button>
          <button class="c4-btn c4-btn--sm" data-action="mode-raw" ${state.renderMode === 'raw' ? 'disabled' : ''}>Raw</button>
          <button class="c4-btn c4-btn--sm" data-action="copy-page">Copy page</button>
          ${canUpdateContext ? '<button class="c4-btn c4-btn--sm" data-action="attach-page">Attach this page</button>' : ''}
          ${
            safeUrl
              ? `<button class="c4-btn c4-btn--sm c4-btn--primary" data-action="recrawl" ${state.recrawling ? 'disabled' : ''}>${state.recrawling ? 'Re-crawling…' : 'Re-crawl this URL'}</button>`
              : ''
          }
        </div>
      </div>
      ${state.recrawlError ? `<div class="c4-error-banner">${escapeHtml(state.recrawlError)}</div>` : ''}
      ${
        state.recrawlPreview
          ? `<div class="c4-panel" style="max-height:220px">
              <div class="c4-header">
                <strong>Live snapshot (${state.recrawlPreview.stats.duration_seconds.toFixed(1)}s)</strong>
                <button class="c4-btn c4-btn--sm c4-btn--ghost" data-action="dismiss-recrawl">Dismiss</button>
              </div>
              <div class="c4-markdown">${renderSafeMarkdown(state.recrawlPreview.preview)}</div>
            </div>`
          : ''
      }
      <div class="c4-pane-scroll">
        ${
          state.renderMode === 'rendered'
            ? `<div class="c4-markdown">${renderSafeMarkdown(current.content)}</div>`
            : `<pre class="c4-raw">${escapeHtml(current.rawSection)}</pre>`
        }
      </div>`
    : '<div class="c4-empty">File is empty.</div>';

  root.innerHTML = `
    <header class="c4-header">
      <div class="c4-title-group">
        <span class="c4-brand-mark">&lt;&gt;</span>
        <h1 class="c4-title">${escapeHtml(state.fileName)}</h1>
      </div>
      <div class="c4-actions">
        <span id="viewer-toast" class="c4-toast">${escapeHtml(state.statusNote)}</span>
        <span class="c4-badge">${state.sections.length} page${state.sections.length === 1 ? '' : 's'} · ${formatBytes(totalBytes)}</span>
      </div>
    </header>

    <div class="c4-explorer-body">
      <div class="c4-split">
        <section class="c4-pane">
          <input id="toc-search" class="c4-input" type="search" placeholder="Filter pages…" value="${escapeHtml(state.tocFilter)}" />
          <div class="c4-pane-scroll">${tocHtml}</div>
        </section>
        <section class="c4-pane">
          ${bodyHtml}
        </section>
      </div>
    </div>
  `;

  const search = document.getElementById('toc-search') as HTMLInputElement | null;
  if (search) {
    search.addEventListener('input', () => {
      state.tocFilter = search.value;
      render();
      const refocused = document.getElementById('toc-search') as HTMLInputElement | null;
      if (refocused) {
        refocused.focus();
        refocused.setSelectionRange(refocused.value.length, refocused.value.length);
      }
    });
  }
}

root.addEventListener('click', (event) => {
  const target = (event.target as HTMLElement | null)?.closest<HTMLElement>(
    '[data-select-page], [data-action]',
  );
  if (!target) return;

  if (target.dataset.selectPage !== undefined) {
    state.selectedIndex = Number(target.dataset.selectPage);
    state.recrawlPreview = null;
    state.recrawlError = null;
    render();
    return;
  }

  const current = state.sections[state.selectedIndex];
  const action = target.dataset.action;
  if (action === 'mode-rendered') {
    state.renderMode = 'rendered';
    render();
  } else if (action === 'mode-raw') {
    state.renderMode = 'raw';
    render();
  } else if (action === 'copy-page' && current) {
    void copyToClipboard(current.rawSection).then((ok) =>
      flashStatus(ok ? 'Copied page!' : 'Clipboard unavailable'),
    );
  } else if (action === 'attach-page' && current) {
    void app
      .updateModelContext({
        content: [
          {
            type: 'text',
            text: `Page "${current.title}"${current.url ? ` (${current.url})` : ''} from ${state.fileName}:\n\n${current.rawSection}`,
          },
        ],
      })
      .then(() => flashStatus('Page attached to next message'))
      .catch(() => flashStatus('Attach unavailable'));
  } else if (action === 'recrawl' && current?.url && isSafeHttpUrl(current.url)) {
    void recrawlCurrentUrl(current.url);
  } else if (action === 'dismiss-recrawl') {
    state.recrawlPreview = null;
    state.recrawlError = null;
    render();
  }
});

wireExternalLinks(root, app);

function handleFileDescriptor(file?: { name?: string; resourceUri?: string }): void {
  if (!file?.resourceUri) return;
  if (file.resourceUri === state.resourceUri && !state.error) return;
  void loadHostFile(file.name ?? 'crawl.md', file.resourceUri);
}

// Register handlers BEFORE connect().
app.ontoolinput = (params) => {
  const args = (params.arguments ?? {}) as { file?: { name?: string; resourceUri?: string } };
  handleFileDescriptor(args.file);
};

app.ontoolresult = (result) => {
  if (result.isError) {
    state.loading = false;
    state.error = extractErrorMessage(result);
    render();
    return;
  }
  const payload = result.structuredContent as FileViewerPayload | undefined;
  handleFileDescriptor(payload?.file);
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
