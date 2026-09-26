import React, { useState, useEffect } from 'react';
import { X, Copy, Check, Download } from 'lucide-react';

interface FeedXmlModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const FeedXmlModal: React.FC<FeedXmlModalProps> = ({ isOpen, onClose }) => {
  const [xml, setXml] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetch('/dekodeko_lj_feed.xml')
        .then((res) => res.text())
        .then((text) => setXml(text))
        .catch((err) => setXml(`<!-- Ошибка загрузки XML: ${err.message} -->`))
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(xml);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([xml], { type: 'application/rss+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dekodeko_lj_feed.xml';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" id="feed-xml-modal">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-xl border border-neutral-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-neutral-900">Сгенерированный RSS 2.0 XML</h3>
            <p className="text-xs text-neutral-500">Путь: /dekodeko_lj_feed.xml</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-lg transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? 'Скопировано!' : 'Копировать'}
            </button>
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-lg transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Скачать
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-neutral-400 hover:text-neutral-700 rounded-lg hover:bg-neutral-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4 bg-neutral-900 text-neutral-100 font-mono text-xs">
          {loading ? (
            <div className="py-12 text-center text-neutral-400">Генерация XML...</div>
          ) : (
            <pre className="whitespace-pre-wrap break-all">{xml}</pre>
          )}
        </div>
      </div>
    </div>
  );
};
