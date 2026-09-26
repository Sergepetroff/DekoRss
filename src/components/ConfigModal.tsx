import React, { useState } from 'react';
import { X, Save, FileCode } from 'lucide-react';
import type { ScraperConfig } from '../types';

interface ConfigModalProps {
  isOpen: boolean;
  config: ScraperConfig;
  onClose: () => void;
  onSave: (newConfig: Partial<ScraperConfig>) => void;
  onParseHtml: (html: string) => void;
}

export const ConfigModal: React.FC<ConfigModalProps> = ({
  isOpen,
  config,
  onClose,
  onSave,
  onParseHtml,
}) => {
  const [ljUrl, setLjUrl] = useState(config.ljUrl);
  const [ljUsername, setLjUsername] = useState(config.ljUsername);
  const [excludedTagsInput, setExcludedTagsInput] = useState(config.excludedTags.join(', '));
  const [rawHtmlInput, setRawHtmlInput] = useState('');
  const [activeTab, setActiveTab] = useState<'config' | 'html'>('config');

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const tags = excludedTagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    onSave({
      ljUrl,
      ljUsername,
      excludedTags: tags,
    });
    onClose();
  };

  const handleCustomHtmlSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawHtmlInput.trim()) return;
    onParseHtml(rawHtmlInput);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" id="config-modal">
      <div className="bg-white rounded-2xl max-w-xl w-full flex flex-col shadow-xl border border-neutral-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('config')}
              className={`text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                activeTab === 'config'
                  ? 'bg-neutral-900 text-white'
                  : 'text-neutral-600 hover:bg-neutral-100'
              }`}
            >
              Параметры скрапера
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('html')}
              className={`text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                activeTab === 'html'
                  ? 'bg-neutral-900 text-white'
                  : 'text-neutral-600 hover:bg-neutral-100'
              }`}
            >
              Парсинг HTML
            </button>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-neutral-400 hover:text-neutral-700 rounded-lg hover:bg-neutral-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {activeTab === 'config' ? (
          <form onSubmit={handleSave} className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-neutral-600 mb-1">
                LJ_URL (URL блога)
              </label>
              <input
                type="text"
                value={ljUrl}
                onChange={(e) => setLjUrl(e.target.value)}
                placeholder="https://dekodeko.livejournal.com"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
                required
              />
              <p className="text-xs text-neutral-500 mt-1">
                Адрес LiveJournal журнала для регулярного скрапинга
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-neutral-600 mb-1">
                Автор блога
              </label>
              <input
                type="text"
                value={ljUsername}
                onChange={(e) => setLjUsername(e.target.value)}
                placeholder="dekodeko"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-neutral-600 mb-1">
                LJ_EXCLUDED_TAGS (Исключаемые теги через запятую)
              </label>
              <input
                type="text"
                value={excludedTagsInput}
                onChange={(e) => setExcludedTagsInput(e.target.value)}
                placeholder="видео, #shorts, оффтоп"
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
              />
              <p className="text-xs text-neutral-500 mt-1">
                Посты с данными тегами отсеиваются и не попадают в RSS-ленту
              </p>
            </div>

            <div className="pt-3 border-t border-neutral-200 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Отмена
              </button>
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-neutral-900 hover:bg-neutral-800 rounded-lg transition-colors"
              >
                <Save className="w-4 h-4" />
                Сохранить параметры
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleCustomHtmlSubmit} className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-neutral-600 mb-1">
                Вставить исходный HTML со страницы LiveJournal
              </label>
              <textarea
                value={rawHtmlInput}
                onChange={(e) => setRawHtmlInput(e.target.value)}
                placeholder="<div class=&quot;entry-wrap--post&quot;>..."
                rows={8}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800"
              />
              <p className="text-xs text-neutral-500 mt-1">
                Позволяет протестировать очистку HTML, форматирование смайлов и генерацию RSS на локальном HTML без обращения к внешнему серверу.
              </p>
            </div>

            <div className="pt-3 border-t border-neutral-200 flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={!rawHtmlInput.trim()}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 rounded-lg transition-colors"
              >
                <FileCode className="w-4 h-4" />
                Распарсить HTML
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
