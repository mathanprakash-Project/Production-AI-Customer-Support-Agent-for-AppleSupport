import React, { useEffect, useState } from 'react';
import { BookOpen, Tag, MessageSquare } from 'lucide-react';
import { api } from '../services/apiClient';
import { IntentItem } from '../types';

export const IntentsPage: React.FC = () => {
  const [intents, setIntents] = useState<IntentItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchIntents = async () => {
      try {
        const data = await api.getIntents();
        setIntents(data);
      } catch (err) {
        console.error('Failed to load intents', err);
      } finally {
        setLoading(false);
      }
    };
    fetchIntents();
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto w-full text-slate-900 dark:text-neutral-100">
      <div className="bg-white dark:bg-neutral-900 p-6 rounded-2xl border border-slate-200 dark:border-neutral-800 shadow-sm">
        <div className="inline-flex items-center space-x-2 px-3 py-1 bg-sky-500/10 border border-sky-500/20 rounded-full text-xs font-bold text-sky-500 mb-2">
          <BookOpen className="h-3.5 w-3.5" />
          <span>Intent Taxonomy & Categorization</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Support Intent Taxonomy</h2>
        <p className="text-xs text-slate-500 dark:text-neutral-400 mt-0.5">
          Structured taxonomy for @AppleSupport generated via embedding clustering and semantic summarization.
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-400 dark:text-neutral-500 text-sm">Loading taxonomy...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {intents.map((item) => (
            <div
              key={item.label}
              className="bg-white dark:bg-neutral-900 p-5 rounded-2xl border border-slate-200 dark:border-neutral-800 shadow-sm flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-center space-x-2 text-sky-500 font-bold text-sm mb-1.5">
                  <Tag className="h-4 w-4 text-sky-500 flex-shrink-0" />
                  <span className="capitalize">{item.label.replace(/_/g, ' ')}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-neutral-400 leading-relaxed">{item.description}</p>
              </div>

              {item.examples && item.examples.length > 0 && (
                <div className="border-t border-slate-100 dark:border-neutral-800 pt-3">
                  <span className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-wider">Sample Queries</span>
                  <div className="mt-1.5 space-y-1">
                    {item.examples.map((ex, idx) => (
                      <div key={idx} className="flex items-start text-xs text-slate-500 dark:text-neutral-400">
                        <MessageSquare className="h-3 w-3 mr-1.5 mt-0.5 text-slate-400 dark:text-neutral-500 flex-shrink-0" />
                        <span className="line-clamp-1 italic">"{ex}"</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
