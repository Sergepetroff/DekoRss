import React, { useState, useEffect } from 'react';
import { FeedHeader } from './components/FeedHeader';
import { PostCard } from './components/PostCard';
import { FeedXmlModal } from './components/FeedXmlModal';
import { ConfigModal } from './components/ConfigModal';
import { DiagnosticsModal } from './components/DiagnosticsModal';
import { Search, Filter, AlertCircle, Info, Sparkles, Activity } from 'lucide-react';
import type { PostItem, ScraperConfig } from './types';

export default function App() {
  const [config, setConfig] = useState<ScraperConfig>({
    ljUrl: 'https://dekodeko.livejournal.com',
    ljUsername: 'dekodeko',
    excludedTags: ['видео', '#shorts'],
    rssFilename: 'dekodeko_lj_feed.xml',
  });

  const [posts, setPosts] = useState<PostItem[]>([]);
  const [isScraping, setIsScraping] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [showExcluded, setShowExcluded] = useState(true);

  const [isXmlModalOpen, setIsXmlModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isDiagnosticsModalOpen, setIsDiagnosticsModalOpen] = useState(false);
  const [bannerMessage, setBannerMessage] = useState<string | null>(null);
  const [bannerType, setBannerType] = useState<'info' | 'error'>('info');

  // Load initial config and posts
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [configRes, postsRes] = await Promise.all([
        fetch('/api/config'),
        fetch('/api/posts'),
      ]);

      if (configRes.ok) {
        const configData = await configRes.json();
        setConfig((prev) => ({ ...prev, ...configData }));
      }

      if (postsRes.ok) {
        const postsData = await postsRes.json();
        setPosts(postsData.posts || []);
        if (postsData.lastUpdated) {
          setLastUpdated(postsData.lastUpdated);
        }
      }
    } catch (err: any) {
      console.warn('Could not connect to API:', err.message);
    }
  };

  const handleRefresh = async () => {
    setIsScraping(true);
    setBannerMessage(null);

    try {
      const res = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ targetUrl: config.ljUrl }),
      });

      const data = await res.json();
      if (data.posts) {
        setPosts(data.posts);
      }
      setLastUpdated(new Date().toUTCString());

      if (data.message) {
        setBannerType('info');
        setBannerMessage(data.message);
      } else {
        setBannerType('info');
        setBannerMessage(`Успешно обработано постов: ${data.count || data.posts?.length}`);
      }
    } catch (err: any) {
      setBannerType('error');
      setBannerMessage(`Ошибка скрапинга: ${err?.message}`);
    } finally {
      setIsScraping(false);
    }
  };

  const handleSaveConfig = async (newConfig: Partial<ScraperConfig>) => {
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.config) {
          setConfig((prev) => ({ ...prev, ...data.config }));
        }
        // Refresh posts list to get updated exclusion statuses
        const postsRes = await fetch('/api/posts');
        if (postsRes.ok) {
          const postsData = await postsRes.json();
          setPosts(postsData.posts || []);
        }
      }
    } catch (err: any) {
      console.error('Failed to update config:', err);
    }
  };

  const handleParseCustomHtml = async (rawHtml: string) => {
    setIsScraping(true);
    try {
      const res = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rawHtml }),
      });
      const data = await res.json();
      if (data.posts) {
        setPosts(data.posts);
        setLastUpdated(new Date().toUTCString());
        setBannerType('info');
        setBannerMessage(`Пользовательский HTML успешно распарсен (${data.posts.length} постов).`);
      }
    } catch (err: any) {
      setBannerType('error');
      setBannerMessage(`Ошибка парсинга HTML: ${err?.message}`);
    } finally {
      setIsScraping(false);
    }
  };

  // Collect all unique tags
  const allTags = Array.from(new Set(posts.flatMap((p) => p.tags)));
  const activePostsCount = posts.filter((p) => !p.isExcluded).length;

  // Filter posts
  const filteredPosts = posts.filter((post) => {
    if (!showExcluded && post.isExcluded) return false;
    if (selectedTag && !post.tags.includes(selectedTag)) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = post.title.toLowerCase().includes(q);
      const matchContent = post.content.toLowerCase().includes(q);
      const matchTag = post.tags.some((t) => t.toLowerCase().includes(q));
      if (!matchTitle && !matchContent && !matchTag) return false;
    }
    return true;
  });

  return (
    <div className="min-h-screen flex flex-col bg-neutral-50 text-neutral-900">
      <FeedHeader
        config={config}
        postCount={posts.length}
        activeCount={activePostsCount}
        isScraping={isScraping}
        lastUpdated={lastUpdated}
        onRefresh={handleRefresh}
        onOpenXml={() => setIsXmlModalOpen(true)}
        onOpenConfig={() => setIsConfigModalOpen(true)}
        onOpenDiagnostics={() => setIsDiagnosticsModalOpen(true)}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6 sm:px-6">
        {/* Diagnostic Callout Banner */}
        <div
          id="diagnostic-callout-banner"
          className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-200/70 text-amber-800 rounded-lg shrink-0">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-amber-950">
                Почему RSS не обновлялся с середины июля?
              </p>
              <p className="text-xs text-amber-800 mt-0.5">
                Обнаружены две ключевые причины: авто-отключение GitHub Actions по неактивности (60 дней) и плашка 18+ Adult Content в ЖЖ.
              </p>
            </div>
          </div>
          <button
            id="open-diagnostic-callout-btn"
            onClick={() => setIsDiagnosticsModalOpen(true)}
            className="px-3 py-1.5 bg-amber-800 hover:bg-amber-900 text-white rounded-lg text-xs font-semibold shrink-0 transition-colors"
          >
            Подробный отчет и тест
          </button>
        </div>

        {/* Notification Banner */}
        {bannerMessage && (
          <div
            className={`mb-6 p-4 rounded-xl text-sm flex items-start gap-3 border ${
              bannerType === 'error'
                ? 'bg-rose-50 border-rose-200 text-rose-800'
                : 'bg-blue-50 border-blue-200 text-blue-800'
            }`}
          >
            {bannerType === 'error' ? (
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            ) : (
              <Info className="w-5 h-5 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p>{bannerMessage}</p>
            </div>
            <button
              onClick={() => setBannerMessage(null)}
              className="text-xs font-semibold underline opacity-70 hover:opacity-100"
            >
              Закрыть
            </button>
          </div>
        )}

        {/* Feature & Pipeline Info Badge */}
        <div className="mb-6 p-4 bg-white rounded-xl border border-neutral-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-neutral-100 text-neutral-700 rounded-lg">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-800">
                Автоматическая очистка HTML & нормализация смайликов
              </p>
              <p className="text-xs text-neutral-500">
                Удаление iframe, тегов LJ, стилей, нормализация ссылок и фиксация размера эмодзи до 18px.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-neutral-600 bg-neutral-50 px-3 py-1.5 rounded-lg border border-neutral-200/60">
            <span>Исключенные теги:</span>
            <div className="flex flex-wrap gap-1">
              {config.excludedTags.map((t) => (
                <span
                  key={t}
                  className="px-1.5 py-0.5 rounded bg-amber-100/80 text-amber-900 font-mono text-[11px]"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Search & Tag Filter Bar */}
        <div className="mb-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск по заголовку или тексту записи..."
              className="w-full pl-9 pr-3 py-2 bg-white border border-neutral-200 rounded-lg text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs text-neutral-600 cursor-pointer select-none bg-white px-3 py-2 rounded-lg border border-neutral-200">
              <input
                type="checkbox"
                checked={showExcluded}
                onChange={(e) => setShowExcluded(e.target.checked)}
                className="rounded text-neutral-900 focus:ring-neutral-800"
              />
              <span>Показывать исключенные ({posts.filter((p) => p.isExcluded).length})</span>
            </label>

            {selectedTag && (
              <button
                type="button"
                onClick={() => setSelectedTag(null)}
                className="text-xs text-neutral-500 hover:text-neutral-900 px-2 py-1 rounded bg-neutral-100"
              >
                Сбросить тег: #{selectedTag} ✕
              </button>
            )}
          </div>
        </div>

        {/* Tag pills */}
        {allTags.length > 0 && (
          <div className="mb-6 flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <span className="text-neutral-400 flex items-center gap-1 shrink-0 mr-1">
              <Filter className="w-3.5 h-3.5" />
              Теги:
            </span>
            <button
              onClick={() => setSelectedTag(null)}
              className={`px-2.5 py-1 rounded-md transition-colors shrink-0 ${
                selectedTag === null
                  ? 'bg-neutral-900 text-white'
                  : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
              }`}
            >
              Все ({posts.length})
            </button>
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() => setSelectedTag(tag === selectedTag ? null : tag)}
                className={`px-2.5 py-1 rounded-md transition-colors shrink-0 ${
                  selectedTag === tag
                    ? 'bg-neutral-900 text-white'
                    : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-100'
                }`}
              >
                #{tag}
              </button>
            ))}
          </div>
        )}

        {/* Post Items */}
        {filteredPosts.length > 0 ? (
          <div className="space-y-4">
            {filteredPosts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-neutral-200 p-12 text-center">
            <p className="text-neutral-600 text-sm mb-2">Записей не найдено</p>
            <p className="text-neutral-400 text-xs">
              Попробуйте изменить поисковый запрос или фильтр по тегам.
            </p>
          </div>
        )}
      </main>

      {/* Modals */}
      <DiagnosticsModal
        isOpen={isDiagnosticsModalOpen}
        onClose={() => setIsDiagnosticsModalOpen(false)}
        onRefreshFeed={handleRefresh}
      />

      <FeedXmlModal
        isOpen={isXmlModalOpen}
        onClose={() => setIsXmlModalOpen(false)}
      />

      <ConfigModal
        isOpen={isConfigModalOpen}
        config={config}
        onClose={() => setIsConfigModalOpen(false)}
        onSave={handleSaveConfig}
        onParseHtml={handleParseCustomHtml}
      />
    </div>
  );
}
