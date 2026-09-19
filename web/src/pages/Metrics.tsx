import { useState, useEffect } from 'react';
import { fetchMetrics } from '../api';
import type { MetricsData } from '../types';

export default function Metrics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MetricsData | null>(null);

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchMetrics();
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="card p-8 text-center text-gray-500 text-sm">Loading...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="card p-8 flex flex-col items-center justify-center gap-4 text-sm text-gray-900">
          <p>Couldn't compute metrics.</p>
          <button 
            onClick={loadMetrics}
            className="px-4 py-2 bg-accent text-white rounded-md font-medium hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-medium tracking-tight text-gray-900">Evaluation Metrics</h1>
        <button 
          onClick={loadMetrics}
          className="px-3 py-1.5 text-sm font-medium bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="card p-6 flex flex-col justify-center">
          <div className="text-sm text-gray-500 font-medium mb-1">Precision</div>
          <div className="text-3xl font-medium tabular-nums text-gray-900">
            {(data.precision * 100).toFixed(1)}%
          </div>
        </div>
        <div className="card p-6 flex flex-col justify-center">
          <div className="text-sm text-gray-500 font-medium mb-1">Recall</div>
          <div className="text-3xl font-medium tabular-nums text-gray-900">
            {(data.recall * 100).toFixed(1)}%
          </div>
        </div>
        <div className="card p-6 flex flex-col justify-center">
          <div className="text-sm text-gray-500 font-medium mb-1">F1 Score</div>
          <div className="text-3xl font-medium tabular-nums text-gray-900">
            {data.f1.toFixed(3)}
          </div>
        </div>
        <div className="card p-6 flex flex-col justify-center bg-gray-50">
          <div className="text-sm text-gray-500 font-medium mb-1">Held-out N</div>
          <div className="text-3xl font-medium tabular-nums text-gray-900">
            {data.n}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50/50 text-sm font-medium text-gray-700">
          Confusion Matrix
        </div>
        <div className="p-6">
          <table className="w-full max-w-md mx-auto text-sm text-center border-collapse">
            <thead>
              <tr>
                <th className="p-2 font-medium text-gray-500 border-b border-r border-transparent"></th>
                <th className="p-2 font-medium text-gray-700 border-b border-gray-200 bg-gray-50">Predicted Contest</th>
                <th className="p-2 font-medium text-gray-700 border-b border-gray-200 bg-gray-50">Predicted Accept</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th className="p-2 font-medium text-gray-700 border-r border-gray-200 bg-gray-50 text-right">Actual Contest</th>
                <td className="p-4 border-b border-r border-gray-200 text-2xl tabular-nums bg-green-50/30 text-green-700 font-medium">
                  {data.confusion.tp}
                </td>
                <td className="p-4 border-b border-gray-200 text-2xl tabular-nums bg-red-50/30 text-red-700 font-medium">
                  {data.confusion.fn}
                </td>
              </tr>
              <tr>
                <th className="p-2 font-medium text-gray-700 border-r border-gray-200 bg-gray-50 text-right">Actual Accept</th>
                <td className="p-4 border-r border-gray-200 text-2xl tabular-nums bg-red-50/30 text-red-700 font-medium">
                  {data.confusion.fp}
                </td>
                <td className="p-4 text-2xl tabular-nums bg-green-50/30 text-green-700 font-medium">
                  {data.confusion.tn}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
