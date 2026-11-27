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
  let inList = false;

  const closeList = () => {
    if (inList) {
      html.push('</ul>');
      inList = false;
    }
  };

  const formatInline = (text: string): string => {
    let out = text;
    // Inline code
    out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
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

    const listItem = line.match(/^\s*[-*]\s+(.*)$/);
    if (listItem) {
      if (!inList) {
        html.push('<ul>');
        inList = true;
      }
      html.push(`<li>${formatInline(listItem[1])}</li>`);
      continue;
    }

    closeList();

    if (/^---+$/.test(line.trim())) {
      html.push('<hr />');
      continue;
    }

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
