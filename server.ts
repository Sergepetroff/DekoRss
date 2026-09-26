import express from 'express';
import cors from 'cors';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { generateRssXml } from './src/cleaner';
import { SAMPLE_POSTS, parseLiveJournalHtml, fetchLiveJournalBlog, runDiagnostics } from './src/scraperService';
import type { PostItem, ScraperConfig } from './src/types';

const PORT = 3000;
const app = express();

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// In-memory config and posts state (per Phase 1.5 and Web constraints)
let config: ScraperConfig = {
  ljUrl: process.env.LJ_URL || 'https://dekodeko.livejournal.com',
  ljUsername: 'dekodeko',
  ljPassword: '',
  excludedTags: (process.env.LJ_EXCLUDED_TAGS || 'видео,#shorts')
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean),
  rssFilename: 'dekodeko_lj_feed.xml',
};

let currentPosts: PostItem[] = [...SAMPLE_POSTS];
let lastUpdated: string = new Date().toUTCString();

function getRssFeedXml(): string {
  return generateRssXml(currentPosts, {
    title: 'dekodeko LiveJournal RSS',
    link: config.ljUrl,
    description: 'Auto-generated RSS from LiveJournal with clean HTML and scaled emojis',
    author: 'dekodeko',
    language: 'ru',
  });
}

// ================= API ENDPOINTS =================

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

// Get current scraper config
app.get('/api/config', (req, res) => {
  res.json({
    ljUrl: config.ljUrl,
    ljUsername: config.ljUsername,
    hasPassword: Boolean(config.ljPassword),
    excludedTags: config.excludedTags,
    rssFilename: config.rssFilename,
  });
});

// Update scraper config
app.post('/api/config', (req, res) => {
  const { ljUrl, ljUsername, ljPassword, excludedTags } = req.body;
  if (ljUrl) config.ljUrl = ljUrl;
  if (ljUsername !== undefined) config.ljUsername = ljUsername;
  if (ljPassword !== undefined) config.ljPassword = ljPassword;
  if (Array.isArray(excludedTags)) {
    config.excludedTags = excludedTags.map((t: string) => t.trim()).filter(Boolean);
    // Recalculate exclusion for current posts
    const excludedSet = new Set(config.excludedTags.map((t) => t.toLowerCase()));
    currentPosts = currentPosts.map((p) => ({
      ...p,
      isExcluded: p.tags.some((tag) => excludedSet.has(tag.toLowerCase())),
    }));
  }
  res.json({ success: true, config: { ...config, ljPassword: undefined } });
});

// Get parsed posts
app.get('/api/posts', (req, res) => {
  res.json({
    posts: currentPosts,
    total: currentPosts.length,
    activeCount: currentPosts.filter((p) => !p.isExcluded).length,
    lastUpdated,
  });
});

// Trigger scraping
app.post('/api/scrape', async (req, res) => {
  const { targetUrl, rawHtml, customExcludedTags } = req.body;
  const scrapeConfig: ScraperConfig = {
    ...config,
    ljUrl: targetUrl || config.ljUrl,
    excludedTags: Array.isArray(customExcludedTags) ? customExcludedTags : config.excludedTags,
  };

  try {
    if (rawHtml) {
      // Direct HTML parse test
      const parsed = parseLiveJournalHtml(rawHtml, {
        ljUrl: scrapeConfig.ljUrl,
        excludedTags: scrapeConfig.excludedTags,
        authorName: scrapeConfig.ljUsername,
      });
      if (parsed.length > 0) {
        currentPosts = parsed;
        lastUpdated = new Date().toUTCString();
        return res.json({
          success: true,
          count: parsed.length,
          posts: parsed,
          source: 'html-input',
        });
      }
    }

    const result = await fetchLiveJournalBlog(scrapeConfig);
    currentPosts = result.posts;
    lastUpdated = new Date().toUTCString();

    res.json({
      success: true,
      count: currentPosts.length,
      activeCount: currentPosts.filter((p) => !p.isExcluded).length,
      posts: currentPosts,
      source: result.source,
      message: result.error,
    });
  } catch (err: any) {
    res.status(500).json({
      success: false,
      error: err?.message || 'Ошибка скрапинга',
    });
  }
});

// Diagnostics endpoint
app.get('/api/diagnostics', async (req, res) => {
  try {
    const diag = await runDiagnostics(config);
    res.json({ success: true, diagnostics: diag });
  } catch (err: any) {
    res.status(500).json({ success: false, error: err?.message || 'Ошибка диагностики' });
  }
});

// RSS Feed Endpoints (exact filename dekodeko_lj_feed.xml from main_scraper.py and deploy.yml)
app.get(['/dekodeko_lj_feed.xml', '/feed.xml', '/rss', '/api/feed.xml'], (req, res) => {
  const xml = getRssFeedXml();
  res.set('Content-Type', 'application/rss+xml; charset=utf-8');
  res.send(xml);
});

// Setup Vite / Static handling
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`LiveJournal RSS Scraper server running on http://0.0.0.0:${PORT}`);
    
    // Auto-scrape live posts on startup in background
    setTimeout(async () => {
      try {
        console.log('Initiating initial LiveJournal scrape...');
        const result = await fetchLiveJournalBlog(config);
        if (result.posts && result.posts.length > 0) {
          currentPosts = result.posts;
          lastUpdated = new Date().toUTCString();
          console.log(`Initial scrape complete: loaded ${currentPosts.length} posts`);
        }
      } catch (err: any) {
        console.warn('Initial scrape warning:', err?.message);
      }
    }, 1000);
  });
}

startServer();
