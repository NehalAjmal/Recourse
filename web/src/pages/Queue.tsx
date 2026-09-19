import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchDisputes } from '../api';
import type { Dispute } from '../types';
import StatusPill from '../components/StatusPill';

type Filter = 'all' | 'contest' | 'escalate' | 'accept';

export default function Queue() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  
  // Basic cursor-based pagination (though we filter client-side for simplicity)
  // To strictly follow the requirement of client-side filtering + pagination,
  // we fetch all currently loaded pages into `disputes`. For a real app,
  // cursor pagination and client-side filtering don't mix perfectly unless you fetch all.
  // The PRD says "Changing it re-fetches or re-filters client-side (either is fine; client-side is simpler for 100 rows)".
  // We'll fetch 100 limit, so we likely get everything in one go, but we'll support a `nextCursor` just in case.
  const [nextCursor, setNextCursor] = useState<string | undefined>(undefined);
  // Track page history to support "Previous" if we need to. But cursor pagination
  // usually means we only go forward. Let's just do a simple "load more" approach if there's a nextCursor.
  // Actually, PRD says: "Previous / Next buttons using the API's cursor".
  // So we need to store cursor history.
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);
  const [currentCursor, setCurrentCursor] = useState<string | undefined>(undefined);

  const loadDisputes = async (cursor?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDisputes(25, cursor);
      setDisputes(res.items);
      setNextCursor(res.next_cursor);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDisputes(currentCursor);
  }, [currentCursor]);

  const handleRefresh = () => {
    loadDisputes(currentCursor);
  };

  const handleNext = () => {
    if (nextCursor) {
      setCursorHistory([...cursorHistory, currentCursor || '']);
      setCurrentCursor(nextCursor);
    }
  };

  const handlePrev = () => {
    if (cursorHistory.length > 0) {
      const newHistory = [...cursorHistory];
      const prev = newHistory.pop();
      setCursorHistory(newHistory);
      setCurrentCursor(prev === '' ? undefined : prev);
    }
  };

  const filtered = disputes.filter(d => filter === 'all' || d.status === filter);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {(['all', 'contest', 'escalate', 'accept'] as Filter[]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${
                filter === f 
                  ? 'bg-accent text-white border-accent' 
                  : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        
        <button 
          onClick={handleRefresh}
          className="px-3 py-1.5 text-sm font-medium bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="card p-8 text-center text-gray-500 text-sm">
          Loading...
        </div>
      ) : error ? (
        <div className="card p-8 flex flex-col items-center justify-center gap-4 text-sm text-gray-900">
          <p>Couldn't load disputes.</p>
          <button 
            onClick={handleRefresh}
            className="px-4 py-2 bg-accent text-white rounded-md font-medium hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-8 text-center text-gray-500 text-sm">
          No disputes match this filter.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50/50">
                <th className="px-4 py-2.5 font-medium text-gray-600">Dispute ID</th>
                <th className="px-4 py-2.5 font-medium text-gray-600">Merchant</th>
                <th className="px-4 py-2.5 font-medium text-gray-600 text-right">Amount</th>
                <th className="px-4 py-2.5 font-medium text-gray-600 text-right">Confidence</th>
                <th className="px-4 py-2.5 font-medium text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(d => (
                <tr 
                  key={d.dispute_id} 
                  onClick={() => navigate(`/disputes/${d.dispute_id}`)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  style={{ height: '36px' }}
                >
                  <td className="px-4 py-1 font-mono text-gray-600 truncate max-w-[120px]" title={d.dispute_id}>
                    {d.dispute_id}
                  </td>
                  <td className="px-4 py-1 text-gray-900">{d.merchant_slug}</td>
                  <td className="px-4 py-1 text-right font-mono tabular-nums text-gray-900">
                    ₹{(d.amount_paise / 100).toFixed(2)}
                  </td>
                  <td className="px-4 py-1 text-right tabular-nums text-gray-600">
                    {(d.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-1">
                    <StatusPill status={d.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {(cursorHistory.length > 0 || nextCursor) && (
            <div className="border-t border-gray-200 p-3 flex justify-end gap-2 bg-gray-50/50">
              <button
                onClick={handlePrev}
                disabled={cursorHistory.length === 0}
                className="px-3 py-1.5 text-sm font-medium bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                onClick={handleNext}
                disabled={!nextCursor}
                className="px-3 py-1.5 text-sm font-medium bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
