import { describe, expect, it } from 'vitest';
import {
  decodeBase64Utf8,
  escapeHtml,
  formatBytes,
  isSafeHttpUrl,
  parseCrawledDocument,
  parsePatternInput,
  renderSafeMarkdown,
} from './shared';

describe('renderSafeMarkdown — XSS protection', () => {
  it('escapes raw script tags and inline event handlers', () => {
    const html = renderSafeMarkdown(
      '<script>alert(1)</script>\n\n<img src=x onerror="alert(2)">',
    );
    expect(html).not.toContain('<script>');
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).toContain('&lt;img src=x onerror=&quot;alert(2)&quot;&gt;');
  });

  it('strips dangerous URL schemes in Markdown links', () => {
    const html = renderSafeMarkdown(
      '[run](javascript:alert(1)) [data](data:text/html,<b>x</b>) [vb](vbscript:msgbox)',
    );
    expect(html).not.toContain('<a ');
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('data:text/html');
    expect(html).toContain('run');
    expect(html).toContain('data');
  });

  it('keeps only safe http(s) links with data-external-link', () => {
    const html = renderSafeMarkdown('Visit [Docs](https://example.com/a?x=1&y=2).');
    expect(html).toContain(
      '<a href="https://example.com/a?x=1&amp;y=2" data-external-link="https://example.com/a?x=1&amp;y=2">Docs</a>',
    );
  });
});

describe('renderSafeMarkdown — formatting fidelity', () => {
  it('protects inline code spans from link and emphasis rules', () => {
    const html = renderSafeMarkdown('Use `[a](https://example.com)` and `*literal*` here.');
    expect(html).toContain('<code>[a](https://example.com)</code>');
    expect(html).toContain('<code>*literal*</code>');
    expect(html).not.toContain('<em>literal</em>');
    expect(html).not.toContain('<a ');
  });

  it('renders unordered and ordered lists while dropping bare empty bullets', () => {
    const html = renderSafeMarkdown('- First\n-\n* Second\n1. Step one\n2. Step two');
    expect(html).toContain('<ul>\n<li>First</li>\n<li>Second</li>\n</ul>');
    expect(html).toContain('<ol>\n<li>Step one</li>\n<li>Step two</li>\n</ol>');
  });

  it('renders headings, blockquotes, horizontal rules, and fenced code blocks', () => {
    const md = '# Title\n\n> Quoted\n\n---\n\n```ts\nconst x = 1 < 2;\n```';
    const html = renderSafeMarkdown(md);
    expect(html).toContain('<h1>Title</h1>');
    expect(html).toContain('<blockquote>Quoted</blockquote>');
    expect(html).toContain('<hr />');
    expect(html).toContain('<pre><code>\nconst x = 1 &lt; 2;\n\n</code></pre>');
  });
});

describe('parseCrawledDocument', () => {
  it('splits multi-page Crawl4AI Markdown exports with metadata', () => {
    const md = [
      '# Home',
      '',
      '## URL',
      'https://docs.example.com/',
      '',
      '## Metadata',
      '- Depth: 0',
      '- Timestamp: 2026-11-27T20:00:00+00:00',
      '',
      '## Content',
      'Welcome home.',
      '',
      '---',
      '',
      '# API Reference',
      '',
      '## URL',
      'https://docs.example.com/api',
      '',
      '## Metadata',
      '- Depth: 1',
      '- Timestamp: 2026-11-27T20:00:02+00:00',
      '',
      '## Content',
      'Endpoints list.',
      '',
      '---',
    ].join('\r\n');

    const sections = parseCrawledDocument(md);
    expect(sections).toHaveLength(2);
    expect(sections[0]).toMatchObject({
      index: 0,
      title: 'Home',
      url: 'https://docs.example.com/',
      depth: '0',
      timestamp: '2026-11-27T20:00:00+00:00',
      content: 'Welcome home.',
    });
    expect(sections[1]).toMatchObject({
      index: 1,
      title: 'API Reference',
      url: 'https://docs.example.com/api',
      depth: '1',
      content: 'Endpoints list.',
    });
  });

  it('falls back to a single section for plain Markdown and empty input', () => {
    expect(parseCrawledDocument('')).toEqual([]);
    const single = parseCrawledDocument('# Notes\n\nPlain body');
    expect(single).toHaveLength(1);
    expect(single[0].title).toBe('Notes');
    expect(single[0].url).toBeNull();
  });
});

describe('shared utilities', () => {
  it('validates http(s) URLs and formats sizes', () => {
    expect(isSafeHttpUrl('https://example.com')).toBe(true);
    expect(isSafeHttpUrl('http://example.com/path')).toBe(true);
    expect(isSafeHttpUrl('file:///etc/passwd')).toBe(false);
    expect(isSafeHttpUrl('javascript:alert(1)')).toBe(false);
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(2048)).toBe('2.0 KB');
    expect(escapeHtml(`"<'&>`)).toBe('&quot;&lt;&#39;&amp;&gt;');
  });

  it('decodes UTF-8 base64 payloads and parses pattern lists', () => {
    const bytes = new TextEncoder().encode('Résumé café — prêt');
    const encoded = btoa(String.fromCharCode(...bytes));
    expect(decodeBase64Utf8(encoded)).toBe('Résumé café — prêt');
    expect(parsePatternInput('/docs/*, */api/*\n *.pdf , ')).toEqual([
      '/docs/*',
      '*/api/*',
      '*.pdf',
    ]);
  });
});
