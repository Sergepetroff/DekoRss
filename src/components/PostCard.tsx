import React, { useState } from 'react';
import { ExternalLink, Tag, Eye, EyeOff, Ban, Calendar } from 'lucide-react';
import type { PostItem } from '../types';

interface PostCardProps {
  post: PostItem;
}

export const PostCard: React.FC<PostCardProps> = ({ post }) => {
  const [showRaw, setShowRaw] = useState(false);

  return (
    <article
      id={`post-${post.id}`}
      className={`bg-white rounded-xl border p-5 transition-shadow hover:shadow-sm ${
        post.isExcluded ? 'border-amber-200 bg-amber-50/30 opacity-75' : 'border-neutral-200'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 mb-3">
        <h2 className="text-lg font-semibold text-neutral-900 leading-snug">
          {post.title}
        </h2>
        <div className="flex items-center gap-2 text-xs text-neutral-500 shrink-0">
          <Calendar className="w-3.5 h-3.5" />
          <span>{post.pubDate}</span>
        </div>
      </div>

      {post.isExcluded && (
        <div className="mb-3 px-3 py-1.5 rounded-lg bg-amber-100 text-amber-800 text-xs flex items-center gap-1.5">
          <Ban className="w-3.5 h-3.5 shrink-0" />
          <span>Пост исключен из итоговой ленты из-за фильтрации тегов</span>
        </div>
      )}

      {/* Content Preview */}
      <div className="prose prose-neutral max-w-none text-neutral-800 text-sm mb-4 leading-relaxed">
        {showRaw ? (
          <pre className="p-3 bg-neutral-100 rounded-lg text-xs font-mono overflow-x-auto whitespace-pre-wrap text-neutral-700">
            {post.content}
          </pre>
        ) : (
          <div
            className="post-html-content space-y-2"
            dangerouslySetInnerHTML={{ __html: post.content }}
          />
        )}
      </div>

      <div className="pt-3 border-t border-neutral-100 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Tags */}
        <div className="flex flex-wrap items-center gap-1.5">
          {post.tags.length > 0 ? (
            post.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-neutral-100 text-neutral-600 hover:bg-neutral-200 transition-colors"
              >
                <Tag className="w-3 h-3 text-neutral-400" />
                {tag}
              </span>
            ))
          ) : (
            <span className="text-neutral-400 italic">Без тегов</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowRaw(!showRaw)}
            className="inline-flex items-center gap-1 text-neutral-600 hover:text-neutral-900"
          >
            {showRaw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            {showRaw ? 'Визуальный вид' : 'Исходный HTML'}
          </button>
          <a
            href={post.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium"
          >
            Открыть в LJ
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </article>
  );
};
