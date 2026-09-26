import * as cheerio from 'cheerio';
import type { PostItem } from './types';

/**
 * Adjusts emoji/emoticon sizes in HTML to prevent them from blowing up in RSS readers.
 * Directly ports fix_emoji_sizes from main_scraper.py.
 */
export function fixEmojiSizes(html: string, size: number = 18): string {
  if (!html) return '';
  const $ = cheerio.load(html, null, false);

  $('img').each((_, el) => {
    const $img = $(el);
    const classes = ($img.attr('class') || '').toLowerCase();
    const src = ($img.attr('src') || '').toLowerCase();

    const isSmiley =
      ['emoji', 'emoticon', 'smiley', 'emote'].some((k) => classes.includes(k)) ||
      ['emoji', 'emoticon', 'smiley', 'smile'].some((k) => src.includes(k));

    if (isSmiley) {
      $img.attr('width', String(size));
      $img.attr('height', String(size));
      let style = $img.attr('style') || '';
      if (!style.includes('width') && !style.includes('height')) {
        style = `${style};width:${size}px;height:${size}px;vertical-align:text-bottom`.replace(/^;/, '');
      }
      $img.attr('style', style);
    } else if ($img.attr('style')) {
      $img.removeAttr('style');
    }
  });

  return $.html();
}

/**
 * Normalizes LiveJournal HTML into clean, predictable RSS content.
 * Directly ports normalize_rss_html and wrap_loose_nodes_in_paragraphs from main_scraper.py.
 */
export function normalizeRssHtml(html: string, ljUrl: string = 'https://dekodeko.livejournal.com'): string {
  if (!html) return '';
  const $ = cheerio.load(html, null, false);

  // Strip non-content and noisy elements
  $('script, style, svg, form, input, button, textarea, div.ljtags').remove();

  // Replace iframe embeds with fallback links
  $('iframe').each((_, el) => {
    const $iframe = $(el);
    const src = $iframe.attr('src') || $iframe.attr('data-src') || '';
    if (src) {
      $iframe.replaceWith(`<p><a href="${src}">Open embedded media</a></p>`);
    } else {
      $iframe.remove();
    }
  });

  // Transform block and layout tags
  $('html, body').each((_, el) => {
    $(el).replaceWith($(el).contents());
  });

  $('div').each((_, el) => {
    const $div = $(el);
    const hasBlockChildren = $div.children('p, div, ul, ol, li, blockquote, pre').length > 0;
    if (hasBlockChildren) {
      $div.replaceWith($div.contents());
    } else {
      // Convert div to paragraph
      $div.replaceWith($(`<p>${$div.html()}</p>`));
    }
  });

  // Unwrap noise container wrappers
  $('span, font, section, article, header, footer, ytd-expander').each((_, el) => {
    $(el).replaceWith($(el).contents());
  });

  // Custom web components except lj-embed
  $('*').each((_, el) => {
    const tagName = (el as any).tagName?.toLowerCase() || '';
    if (tagName.includes('-') && tagName !== 'lj-embed') {
      $(el).replaceWith($(el).contents());
    }
  });

  const allowedTags = new Set([
    'a', 'b', 'blockquote', 'br', 'code', 'em', 'i', 'img',
    'li', 'ol', 'p', 'pre', 'strong', 'sub', 'sup', 'u', 'ul'
  ]);

  const allowedAttrs: Record<string, Set<string>> = {
    a: new Set(['href', 'title']),
    img: new Set(['src', 'alt', 'title', 'width', 'height', 'style']),
  };

  // Filter tags and attributes
  $('*').each((_, el) => {
    const tagName = (el as any).tagName?.toLowerCase() || '';
    if (!allowedTags.has(tagName)) {
      $(el).replaceWith($(el).contents());
      return;
    }

    const attrs = (el as any).attribs || {};
    const keep = allowedAttrs[tagName] || new Set();
    for (const attr of Object.keys(attrs)) {
      if (!keep.has(attr)) {
        $(el).removeAttr(attr);
      }
    }

    // Rewrite relative links
    if (tagName === 'a') {
      let href = ($(el).attr('href') || '').trim();
      if (!href) {
        $(el).replaceWith($(el).contents());
      } else if (href.startsWith('//')) {
        $(el).attr('href', `https:${href}`);
      } else if (href.startsWith('/') && ljUrl) {
        $(el).attr('href', `${ljUrl.replace(/\/+$/, '')}${href}`);
      }
    }

    // Rewrite relative image urls
    if (tagName === 'img') {
      let src = ($(el).attr('src') || '').trim();
      if (!src) {
        $(el).remove();
      } else if (src.startsWith('//')) {
        $(el).attr('src', `https:${src}`);
      }
    }
  });

  let output = $.html();
  // Collapse excessive <br>
  output = output.replace(/(?:\s*<br\s*\/?>\s*){3,}/gi, '<br/><br/>');

  // Strip empty paragraphs
  const clean$ = cheerio.load(output, null, false);
  clean$('p').each((_, el) => {
    const $p = clean$(el);
    const text = $p.text().trim();
    const hasImg = $p.find('img').length > 0;
    if (!text && !hasImg) {
      $p.remove();
    }
  });

  return clean$.html();
}

/**
 * Generates standards-compliant RSS 2.0 XML feed with CDATA content.
 */
export function generateRssXml(
  posts: PostItem[],
  options: {
    title: string;
    link: string;
    description: string;
    author: string;
    language?: string;
  }
): string {
  const lang = options.language || 'ru';
  const now = new Date().toUTCString();

  const itemsXml = posts
    .filter((p) => !p.isExcluded)
    .map((post) => {
      const pubDate = post.pubDate || now;
      const title = escapeXml(post.title || 'No Title');
      const link = escapeXml(post.link);
      const guid = escapeXml(post.guid || post.link);

      return `    <item>
      <title>${title}</title>
      <link>${link}</link>
      <guid isPermaLink="${post.link ? 'true' : 'false'}">${guid}</guid>
      <pubDate>${pubDate}</pubDate>
      <description><![CDATA[${post.content}]]></description>
      <content:encoded><![CDATA[${post.content}]]></content:encoded>
    </item>`;
    })
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(options.title)}</title>
    <link>${escapeXml(options.link)}</link>
    <description>${escapeXml(options.description)}</description>
    <language>${lang}</language>
    <lastBuildDate>${now}</lastBuildDate>
    <generator>DekoRss / Node.js RSS Generator</generator>
    <atom:link href="${escapeXml(options.link)}/dekodeko_lj_feed.xml" rel="self" type="application/rss+xml" />
${itemsXml}
  </channel>
</rss>`;
}

function escapeXml(unsafe: string): string {
  return (unsafe || '').replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case '<': return '&lt;';
      case '>': return '&gt;';
      case '&': return '&amp;';
      case '\'': return '&apos;';
      case '"': return '&quot;';
      default: return c;
    }
  });
}
