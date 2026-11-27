import {
  App,
  applyDocumentTheme,
  applyHostStyleVariables,
  type McpUiHostContext,
} from '@modelcontextprotocol/ext-apps';
import { z } from 'zod';

export interface CrawlStats {
  successful_pages: number;
  failed_pages: number;
  not_found_pages: number;
  forbidden_pages: number;
  duration_seconds: number;
}

export interface CrawlLink {
  href: string;
  text?: string;
}

export interface SkippedPage {
  url: string;
  reason: string;
}

export interface CrawlCardPayload {
  kind: 'crawl' | 'crawl_page';
  status: 'completed' | 'partial' | 'empty';
  url: string;
  file_path?: string | null;
  file_uri?: string | null;
  result_name?: string | null;
  resource_uri?: string | null;
  stats: CrawlStats;
  links: {
    internal: CrawlLink[];
    external: CrawlLink[];
    total_internal: number;
    total_external: number;
  };
  skipped: SkippedPage[];
  total_skipped: number;
  preview: string;
  preview_truncated: boolean;
  content_truncated: boolean;
  timed_out: boolean;
}

export interface SavedResultEntry {
  uri: string;
  name: string;
  size_bytes: number;
  modified: string;
  source_url: string | null;
  file_uri?: string | null;
}

export interface ExplorerPayload {
  kind: 'explorer';
  results: SavedResultEntry[];
  total_results?: number;
  offset?: number;
  limit?: number;
  has_more?: boolean;
  sessions: string[];
  selected_result?: string | null;
  initial_url?: string | null;
  allow_js?: boolean;
  allow_private_networks?: boolean;
}

export interface ListResultsPayload {
  results: SavedResultEntry[];
  total_results: number;
  total_all?: number;
  offset: number;
  limit: number;
  has_more: boolean;
  query?: string;
  sessions: string[];
}

export interface ReadResultPayload {
  name: string;
  uri: string;
  file_uri?: string | null;
  content: string;
  size_bytes: number;
}

export interface SearchMatch {
  uri: string;
  name: string;
  file_uri?: string | null;
  size_bytes: number;
  modified: string;
  source_url: string | null;
  line: number;
  snippet: string;
  match_count: number;
}

export interface SearchResultsPayload {
  query: string;
  matches: SearchMatch[];
  total_matches: number;
}

export interface CrawledPageSection {
  index: number;
  title: string;
  url: string | null;
  depth: string | null;
  timestamp: string | null;
  content: string;
  rawSection: string;
}

export interface FileViewerPayload {
  kind: 'file_viewer';
  file?: {
    name?: string;
    resourceUri?: string;
  };
}

export function applyThemeFromContext(ctx?: McpUiHostContext): void {
  if (!ctx) return;
  if (ctx.theme) {
    applyDocumentTheme(ctx.theme);
  }
  if (ctx.styles?.variables) {
    applyHostStyleVariables(ctx.styles.variables);
  }
}

export function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function isSafeHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Render untrusted Markdown safely by HTML-escaping first and only allowing
 * http(s) links (which are intercepted to open via app.openLink).
 */
export function renderSafeMarkdown(markdown: string): string {
  const escaped = escapeHtml(markdown.replace(/\r\n/g, '\n'));
  const lines = escaped.split('\n');
  const html: string[] = [];
  let inCodeBlock = false;
  let listTag: 'ul' | 'ol' | null = null;

  const closeList = () => {
    if (listTag) {
      html.push(`</${listTag}>`);
      listTag = null;
    }
  };

  const formatInline = (text: string): string => {
    // Protect inline code spans before applying link/emphasis replacements.
    const codeSpans: string[] = [];
    let out = text.replace(/`([^`]+)`/g, (_m, code: string) => {
      const idx = codeSpans.push(`<code>${code}</code>`) - 1;
      return `\u0000CODE${idx}\u0000`;
    });
    // Markdown links [label](url) — strictly allow http(s)
    out = out.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, label: string, rawUrl: string) => {
      const unescapedUrl = rawUrl.replace(/&amp;/g, '&');
      if (!isSafeHttpUrl(unescapedUrl)) {
        return label;
      }
      return `<a href="${escapeHtml(unescapedUrl)}" data-external-link="${escapeHtml(unescapedUrl)}">${label}</a>`;
    });
    // Bold and italic
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Restore protected inline code spans
    out = out.replace(/\u0000CODE(\d+)\u0000/g, (_m, idx: string) => codeSpans[Number(idx)] ?? '');
    return out;
  };

  for (const line of lines) {
    if (line.trimStart().startsWith('```')) {
      closeList();
      if (!inCodeBlock) {
        html.push('<pre><code>');
        inCodeBlock = true;
      } else {
        html.push('</code></pre>');
        inCodeBlock = false;
      }
      continue;
    }

    if (inCodeBlock) {
      html.push(`${line}\n`);
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${formatInline(heading[2])}</h${level}>`);
      continue;
    }

    if (/^---+$/.test(line.trim())) {
      closeList();
      html.push('<hr />');
      continue;
    }

    const unorderedItem = line.match(/^\s*[-*](?:\s+(.*)|\s*)$/);
    if (unorderedItem) {
      const itemBody = (unorderedItem[1] ?? '').trim();
      if (!itemBody) continue;
      if (listTag !== 'ul') {
        closeList();
        html.push('<ul>');
        listTag = 'ul';
      }
      html.push(`<li>${formatInline(itemBody)}</li>`);
      continue;
    }

    const orderedItem = line.match(/^\s*\d+\.\s+(.*)$/);
    if (orderedItem) {
      const itemBody = orderedItem[1].trim();
      if (!itemBody) continue;
      if (listTag !== 'ol') {
        closeList();
        html.push('<ol>');
        listTag = 'ol';
      }
      html.push(`<li>${formatInline(itemBody)}</li>`);
      continue;
    }

    closeList();

    if (line.startsWith('&gt; ')) {
      html.push(`<blockquote>${formatInline(line.slice(5))}</blockquote>`);
      continue;
    }

    if (line.trim() === '') {
      continue;
    }

    html.push(`<p>${formatInline(line)}</p>`);
  }

  closeList();
  if (inCodeBlock) {
    html.push('</code></pre>');
  }

  return html.join('\n');
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export function wireExternalLinks(container: HTMLElement, app: App): void {
  container.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    const anchor = target?.closest<HTMLAnchorElement>('a[data-external-link]');
    if (!anchor) return;
    event.preventDefault();
    const url = anchor.dataset.externalLink;
    if (url && isSafeHttpUrl(url)) {
      void app.openLink({ url }).catch(() => {
        // Host may not support openLinks
      });
    }
  });
}

const ToggleAuxPaneResultSchema = z.object({ isError: z.boolean().optional() }).passthrough();

export async function openFileInAuxPane(app: App, fileUri: string): Promise<boolean> {
  try {
    const res = await app.request(
      {
        method: 'com.google.antigravity/toggle-aux-pane',
        params: { tabType: 'fileView', uri: fileUri },
      },
      ToggleAuxPaneResultSchema,
    );
    return !res.isError;
  } catch {
    return false;
  }
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function extractErrorMessage(result: { content?: Array<{ type?: string; text?: string }> }): string {
  const first = result.content?.find((c) => c.type === 'text' && typeof c.text === 'string');
  return first?.text ?? 'Request failed.';
}

/**
 * Split a Crawl4AI multi-page Markdown export into structured page sections.
 * Falls back to a single section when the Markdown does not match the format.
 */
export function parseCrawledDocument(markdown: string): CrawledPageSection[] {
  const normalized = markdown.replace(/\r\n/g, '\n').trim();
  if (!normalized) return [];

  // Crawl4AI writes each page starting with "# <Title>\n\n## URL\n<url>\n..."
  const starts: number[] = [];
  const markerRe = /(?:^|\n)(# [^\n]+\n+## URL\n\S+)/g;
  let match: RegExpExecArray | null;
  while ((match = markerRe.exec(normalized)) !== null) {
    const startIdx = match.index + (match[0].startsWith('\n') ? 1 : 0);
    starts.push(startIdx);
  }

  if (starts.length === 0) {
    const firstHeading = normalized.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? 'Document';
    return [
      {
        index: 0,
        title: firstHeading,
        url: null,
        depth: null,
        timestamp: null,
        content: normalized,
        rawSection: normalized,
      },
    ];
  }

  const sections: CrawledPageSection[] = [];
  for (let i = 0; i < starts.length; i++) {
    const end = i + 1 < starts.length ? starts[i + 1] : normalized.length;
    const rawChunk = normalized.slice(starts[i], end).replace(/\n+---\s*$/, '').trim();
    const title = rawChunk.match(/^#\s+(.+)$/m)?.[1]?.trim() ?? `Page ${i + 1}`;
    const url = rawChunk.match(/^## URL\n(\S+)/m)?.[1]?.trim() ?? null;
    const depth = rawChunk.match(/^- Depth:\s*(.+)$/m)?.[1]?.trim() ?? null;
    const timestamp = rawChunk.match(/^- Timestamp:\s*(.+)$/m)?.[1]?.trim() ?? null;
    const contentIdx = rawChunk.search(/^## Content\s*$/m);
    const content =
      contentIdx >= 0 ? rawChunk.slice(contentIdx).replace(/^## Content\s*\n?/, '').trim() : rawChunk;

    sections.push({
      index: i,
      title,
      url,
      depth,
      timestamp,
      content,
      rawSection: rawChunk,
    });
  }
  return sections;
}

export function decodeBase64Utf8(base64: string): string {
  const binary = atob(base64);
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
  return new TextDecoder('utf-8').decode(bytes);
}

export function parsePatternInput(raw: string): string[] {
  return raw
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
}
