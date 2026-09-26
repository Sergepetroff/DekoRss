import React, { useState, useEffect } from 'react';
import { X, Activity, AlertTriangle, CheckCircle2, RefreshCw, ShieldAlert, Clock, Filter, ExternalLink } from 'lucide-react';
import type { DiagnosticResult } from '../scraperService';

interface DiagnosticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefreshFeed: () => void;
}

export const DiagnosticsModal: React.FC<DiagnosticsModalProps> = ({ isOpen, onClose, onRefreshFeed }) => {
  const [data, setData] = useState<DiagnosticResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDiagnostics = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/diagnostics');
      const json = await res.json();
      if (json.success && json.diagnostics) {
        setData(json.diagnostics);
      } else {
        setError(json.error || 'Не удалось получить диагностические данные');
      }
    } catch (err: any) {
      setError(err?.message || 'Ошибка запроса к серверу');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDiagnostics();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      id="diagnostics-modal-overlay"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-neutral-900/60 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div
        id="diagnostics-modal-container"
        className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-neutral-200 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-amber-100 text-amber-800 rounded-xl">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-neutral-900">
                Диагностика: почему RSS не обновлялся с июля?
              </h2>
              <p className="text-xs text-neutral-500">
                Анализ работы оригинального воркфлоу GitHub Actions и платформы LiveJournal
              </p>
            </div>
          </div>
          <button
            id="close-diagnostics-btn"
            onClick={onClose}
            className="p-1.5 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mt-5 space-y-4">
          {/* Main Root Cause 1: GitHub Actions Inactivity */}
          <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-xl">
            <div className="flex items-start gap-3">
              <Clock className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-amber-900">
                  1. Авто-приостановка по расписанию в GitHub Actions (правило 60 дней)
                </h3>
                <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                  В GitHub Actions cron-расписание (<code className="bg-amber-100 px-1 py-0.5 rounded text-[11px]">schedule: - cron: '0 0/6 * * *'</code>)
                  <strong> автоматически отключается через 60 дней бездействия репозитория</strong> (если не было новых коммитов).
                  Если проект перестал обновляться именно с середины июля, то ровно в этот момент истек 60-дневный лимит со времени последнего коммита в репозиторий.
                </p>
                <div className="mt-2 text-xs text-amber-900 font-medium">
                  <strong>Как исправить в GitHub:</strong> Откройте вкладку <em>Actions</em> в вашем репозитории, выберите воркфлоу «Generate and Publish RSS» и нажмите кнопку <strong>«Enable workflow»</strong> (либо сделайте любой пустой коммит в ветку main).
                </div>
              </div>
            </div>
          </div>

          {/* Root Cause 2: 18+ Adult Content Notice on LiveJournal */}
          <div className="p-4 bg-rose-50/70 border border-rose-200 rounded-xl">
            <div className="flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-rose-700 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-rose-900">
                  2. Плашка «+18 Adult Content Notice» LiveJournal
                </h3>
                <p className="text-xs text-rose-800 mt-1 leading-relaxed">
                  Блог <span className="font-semibold">dekodeko.livejournal.com</span> отмечен как контент для взрослых. При обращении обычного HTTP-скрапера или незалогиненного Playwright без специального cookie LiveJournal отдает страницу с предупреждением 18+ и <strong>0 постов</strong>.
                </p>
                <p className="text-xs text-rose-800 mt-1.5 leading-relaxed">
                  <strong>Решение:</strong> Наш обновленный скрапер теперь автоматически передает заголовок <code className="bg-rose-100 px-1 py-0.5 rounded text-[11px]">Cookie: adult_explicit=1</code> на каждый запрос, что гарантирует получение актуальных постов без необходимости ручной авторизации.
                </p>
              </div>
            </div>
          </div>

          {/* Root Cause 3: Playwright & Cloud IP Blocking */}
          <div className="p-4 bg-neutral-50 border border-neutral-200 rounded-xl">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-neutral-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-neutral-900">
                  3. Блокировка авторизации Playwright со стороны Rambler/LJ
                </h3>
                <p className="text-xs text-neutral-600 mt-1 leading-relaxed">
                  Оригинальный скрипт <code className="bg-neutral-100 px-1 py-0.5 rounded text-[11px]">main_scraper.py</code> логинился в ЖЖ через Playwright (headless Chromium). В последнее время Rambler SSO блокирует попытки входа с диапазонов IP облачных раннеров GitHub Actions (Microsoft Azure) и показывает SmartCaptcha, что приводило к ошибке таймаута и завершению шага генерации RSS.
                </p>
              </div>
            </div>
          </div>

          {/* Root Cause 4: Tags Filtering */}
          <div className="p-4 bg-neutral-50 border border-neutral-200 rounded-xl">
            <div className="flex items-start gap-3">
              <Filter className="w-5 h-5 text-neutral-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-neutral-900">
                  4. Фильтрация тегов (LJ_EXCLUDED_TAGS)
                </h3>
                <p className="text-xs text-neutral-600 mt-1 leading-relaxed">
                  У автора много постов с тегами <span className="font-mono text-neutral-800">видео</span> и <span className="font-mono text-neutral-800">#shorts</span>. Если за определенный период автор публиковал только ролики, все они отбрасывались фильтром, и лента казалась «застывшей».
                </p>
              </div>
            </div>
          </div>

          {/* Live Check Results */}
          <div className="p-4 bg-blue-50/60 border border-blue-200 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-blue-900 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-blue-600" />
                Результаты проверки в реальном времени
              </h3>
              <button
                onClick={fetchDiagnostics}
                disabled={isLoading}
                className="text-xs text-blue-700 hover:text-blue-900 inline-flex items-center gap-1 font-medium disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
                Повторить тест
              </button>
            </div>

            {isLoading ? (
              <div className="py-4 text-center text-xs text-neutral-500">
                Выполняется проверка LiveJournal...
              </div>
            ) : data ? (
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-blue-100">
                  <span className="text-neutral-600">Запрос без cookie 18+:</span>
                  <span className="font-semibold text-rose-700">
                    {data.liveJournalAccess.withoutCookiePosts} постов (активен блок «Adult Notice»)
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-blue-100">
                  <span className="text-neutral-600">Запрос с cookie adult_explicit=1:</span>
                  <span className="font-semibold text-emerald-700">
                    {data.liveJournalAccess.withCookiePosts} постов успешно получено
                  </span>
                </div>
                {data.latestPostDetected && (
                  <div className="flex justify-between py-1 border-b border-blue-100">
                    <span className="text-neutral-600">Последний пост в ЖЖ:</span>
                    <span className="font-medium text-neutral-800 truncate max-w-[280px]">
                      {data.latestPostDetected.title} ({data.latestPostDetected.date})
                    </span>
                  </div>
                )}
                <div className="flex justify-between py-1">
                  <span className="text-neutral-600">Статус генерации RSS:</span>
                  <span className="font-semibold text-emerald-700">Работает стабильно</span>
                </div>
              </div>
            ) : error ? (
              <p className="text-xs text-rose-600">{error}</p>
            ) : null}
          </div>
        </div>

        <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-neutral-200">
          <a
            href="https://github.com/Sergepetroff/DekoRss/actions"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-600 hover:text-neutral-900 inline-flex items-center gap-1 underline"
          >
            Открыть GitHub Actions репозитория <ExternalLink className="w-3 h-3" />
          </a>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                onClose();
                onRefreshFeed();
              }}
              className="px-4 py-2 bg-neutral-900 hover:bg-neutral-800 text-white text-xs font-semibold rounded-lg transition-colors shadow-sm"
            >
              Запустить обновление ленты
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
