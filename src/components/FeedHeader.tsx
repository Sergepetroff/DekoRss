import React from 'react';
import { Rss, RefreshCw, Settings, Code, ExternalLink, Download, Activity } from 'lucide-react';
import type { ScraperConfig } from '../types';

interface FeedHeaderProps {
  config: ScraperConfig;
  postCount: number;
  activeCount: number;
  isScraping: boolean;
  lastUpdated: string;
  onRefresh: () => void;
  onOpenXml: () => void;
  onOpenConfig: () => void;
  onOpenDiagnostics: () => void;
}

export const FeedHeader: React.FC<FeedHeaderProps> = ({
  config,
  postCount,
  activeCount,
  isScraping,
  lastUpdated,
  onRefresh,
  onOpenXml,
  onOpenConfig,
  onOpenDiagnostics,
}) => {
  return (
    <header className="border-b border-neutral-200 bg-white" id="main-header">
      <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-3 bg-amber-50 text-amber-700 rounded-xl border border-amber-200">
              <Rss className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-neutral-900">
                  DekoRss LiveJournal Feed
                </h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  RSS 2.0 Активен
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1 text-sm text-neutral-500">
                <a
                  href={config.ljUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-neutral-800 underline inline-flex items-center gap-1"
                >
                  {config.ljUrl}
                  <ExternalLink className="w-3 h-3" />
                </a>
                <span>•</span>
                <span>
                  {activeCount} из {postCount} постов в ленте
                </span>
                {lastUpdated && (
                  <>
                    <span>•</span>
                    <span>Обновлено: {new Date(lastUpdated).toLocaleTimeString()}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <a
              id="download-feed-btn"
              href="/dekodeko_lj_feed.xml"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              Feed XML
            </a>

            <button
              id="view-xml-btn"
              onClick={onOpenXml}
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 rounded-lg transition-colors"
            >
              <Code className="w-4 h-4" />
              Просмотр XML
            </button>

            <button
              id="diagnostics-btn"
              onClick={onOpenDiagnostics}
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200/80 rounded-lg transition-colors"
            >
              <Activity className="w-4 h-4 text-amber-600" />
              Диагностика
            </button>

            <button
              id="config-btn"
              onClick={onOpenConfig}
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-neutral-700 bg-neutral-100 hover:bg-neutral-200 rounded-lg transition-colors"
            >
              <Settings className="w-4 h-4" />
              Настройки
            </button>

            <button
              id="scrape-btn"
              onClick={onRefresh}
              disabled={isScraping}
              type="button"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 rounded-lg shadow-sm transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isScraping ? 'animate-spin' : ''}`} />
              {isScraping ? 'Скрапинг...' : 'Обновить ленту'}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
