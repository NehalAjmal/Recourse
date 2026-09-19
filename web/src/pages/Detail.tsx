import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchDispute, fetchAudit } from '../api';
import type { Dispute, AuditEntry } from '../types';
import StatusPill from '../components/StatusPill';

export default function Detail() {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [showAudit, setShowAudit] = useState(false);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    
    try {
      const [disputeRes, auditRes] = await Promise.all([
        fetchDispute(id),
        fetchAudit(id)
      ]);
      setDispute(disputeRes);
      setAudit(auditRes.entries);
    } catch (err) {
      if (err instanceof Error && err.message === 'NOT_FOUND') {
        setNotFound(true);
      } else {
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const formatTime = (ts: number) => {
    // Keep ISO-ish as requested (2026-09-18 14:03 UTC)
    const d = new Date(ts * 1000);
    return d.toISOString().replace('T', ' ').substring(0, 16) + ' UTC';
  };

  if (loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <Link to="/" className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
          &larr; Back to queue
        </Link>
        <div className="card p-12 text-center text-gray-500 text-sm">
          Loading...
        </div>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <div className="card p-12 flex flex-col items-center justify-center gap-4 text-sm text-gray-900">
          <p>This dispute doesn't exist.</p>
          <Link to="/" className="px-4 py-2 bg-accent text-white rounded-md font-medium hover:bg-blue-700 transition-colors">
            Back to queue
          </Link>
        </div>
      </div>
    );
  }

  if (error || !dispute) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <div className="card p-12 flex flex-col items-center justify-center gap-4 text-sm text-gray-900">
          <p>Couldn't load this dispute.</p>
          <div className="flex gap-3">
            <button 
              onClick={loadData}
              className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-md font-medium hover:bg-gray-50 transition-colors"
            >
              Retry
            </button>
            <Link to="/" className="px-4 py-2 bg-accent text-white rounded-md font-medium hover:bg-blue-700 transition-colors">
              Back to queue
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <Link to="/" className="inline-block text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors">
        &larr; Back to queue
      </Link>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-medium font-mono text-gray-900 tracking-tight">{dispute.dispute_id}</h1>
          <StatusPill status={dispute.status} />
        </div>
        <div className="text-sm font-medium text-gray-600">
          Confidence: <span className="font-mono tabular-nums text-gray-900 ml-1">{(dispute.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Mandate */}
        <div className="card p-5 space-y-3">
          <h2 className="text-sm font-medium text-gray-900">Mandate</h2>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Merchant</span>
              <span className="text-gray-900 font-medium">{dispute.mandate?.merchant_slug || dispute.merchant_slug}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Spend Cap</span>
              <span className="text-gray-900 font-mono tabular-nums">₹{((dispute.mandate?.spend_cap_paise || 0) / 100).toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Status</span>
              <span className="text-gray-900">{dispute.mandate?.status || 'unknown'}</span>
            </div>
          </div>
        </div>

        {/* Action Log */}
        <div className="card p-5 space-y-3">
          <div className="space-y-0.5">
            <h2 className="text-sm font-medium text-gray-900">Agent Action Log</h2>
            <p className="text-xs text-gray-500">Synthetic click trail standing in for real navigation</p>
          </div>
          <div className="space-y-2 text-sm">
            {dispute.actions.map(a => (
              <div key={a.seq} className="flex justify-between border-l-2 border-gray-200 pl-3">
                <span className="font-medium text-gray-700 capitalize">{a.action}</span>
                <span className="text-gray-500 font-mono tabular-nums">{formatTime(a.ts)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Fulfilment */}
        <div className="card p-5 space-y-3">
          <h2 className="text-sm font-medium text-gray-900">Fulfilment</h2>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Order ID</span>
              <span className="text-gray-900 font-mono truncate max-w-[120px]" title={dispute.fulfilment.order_id}>
                {dispute.fulfilment.order_id}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Delivered</span>
              <span className="text-gray-900">{dispute.fulfilment.delivered ? 'Yes' : 'No'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Time</span>
              <span className="text-gray-900 font-mono tabular-nums">
                {dispute.fulfilment.delivered_ts ? formatTime(dispute.fulfilment.delivered_ts) : '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Amount</span>
              <span className="text-gray-900 font-mono tabular-nums">₹{dispute.fulfilment.amount_paise / 100}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Six Checks */}
      <div className="card overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-200 bg-gray-50/50 text-sm font-medium text-gray-900">
          Evaluation Checks
        </div>
        <div className="divide-y divide-gray-100">
          {dispute.checks.map(c => (
            <div key={c.id} className="p-4 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
              <div className="flex items-center gap-3 min-w-[200px]">
                <span className={`inline-flex items-center justify-center w-5 h-5 rounded-sm text-xs font-bold ${
                  c.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {c.passed ? '✓' : '✗'}
                </span>
                <span className="text-sm font-medium text-gray-900">{c.name}</span>
              </div>
              
              <div className="flex-1 text-sm text-gray-600">
                {c.detail}
              </div>
              
              <div className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                {c.engine}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Narrative or Escalation Reason */}
      <div className="card p-6 border-l-4 border-l-accent">
        {dispute.grounded && dispute.narrative ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium text-gray-900">Narrative Summary</h2>
              <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-sm font-medium border border-gray-200">
                Grounded
              </span>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed max-w-4xl">
              {dispute.narrative}
            </p>
          </div>
        ) : dispute.escalation_reason ? (
          <div className="space-y-2">
            <h2 className="text-sm font-medium text-gray-900">Escalation Reason</h2>
            <p className="text-sm text-gray-700 leading-relaxed max-w-4xl">
              {dispute.escalation_reason}
            </p>
          </div>
        ) : (
          <div className="text-sm text-gray-500 italic">No narrative or escalation reason recorded.</div>
        )}
      </div>

      {/* Audit Log */}
      <div className="card overflow-hidden">
        <button 
          onClick={() => setShowAudit(!showAudit)}
          className="w-full px-5 py-3 flex items-center justify-between bg-gray-50/50 hover:bg-gray-50 transition-colors text-left"
        >
          <span className="text-sm font-medium text-gray-900">Audit Log</span>
          <span className="text-sm text-accent font-medium">
            {showAudit ? 'Hide audit log' : 'Show audit log'}
          </span>
        </button>
        
        {showAudit && (
          <div className="border-t border-gray-200 divide-y divide-gray-100">
            {audit.length === 0 ? (
              <div className="p-5 text-sm text-gray-500 text-center">No audit entries found.</div>
            ) : (
              // Reverse chronological
              [...audit].reverse().map((a, i) => (
                <div key={i} className="p-4 grid grid-cols-1 md:grid-cols-4 gap-2 md:gap-4 text-sm">
                  <div className="font-mono tabular-nums text-gray-500 md:col-span-1">
                    {formatTime(a.ts)}
                  </div>
                  <div className="md:col-span-3 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{a.actor}</span>
                      <span className="text-gray-400">·</span>
                      <span className="text-gray-700">{a.event}</span>
                    </div>
                    {a.from_status !== a.to_status && (
                      <div className="text-xs text-gray-500">
                        Status changed: <span className="font-mono">{a.from_status}</span> &rarr; <span className="font-mono">{a.to_status}</span>
                      </div>
                    )}
                    {a.detail && (
                      <div className="text-gray-600 mt-1">{a.detail}</div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

    </div>
  );
}
