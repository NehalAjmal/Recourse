import type { Dispute, AuditEntry, MetricsData } from './types';

// Using the relative path since Vite proxies /api to the real backend in dev.
// In production on Amplify, we can just use the absolute URL, but API Gateway URL is typically fixed.
const API_BASE = '/api';

async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 8000);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  } catch (err) {
    clearTimeout(id);
    throw err;
  }
}

export async function fetchDisputes(limit = 25, cursor?: string): Promise<{items: Dispute[], next_cursor?: string}> {
  const url = new URL(`${API_BASE}/disputes`, window.location.origin);
  url.searchParams.set('limit', limit.toString());
  if (cursor) {
    url.searchParams.set('cursor', cursor);
  }
  
  const res = await fetchWithTimeout(url.toString());
  if (!res.ok) throw new Error('Failed to fetch disputes');
  return res.json();
}

export async function fetchDispute(id: string): Promise<Dispute> {
  const res = await fetchWithTimeout(`${API_BASE}/disputes/${id}`);
  if (res.status === 404) throw new Error('NOT_FOUND');
  if (!res.ok) throw new Error('Failed to fetch dispute');
  return res.json();
}

export async function fetchAudit(id: string): Promise<{entries: AuditEntry[]}> {
  const res = await fetchWithTimeout(`${API_BASE}/disputes/${id}/audit`);
  if (!res.ok) throw new Error('Failed to fetch audit log');
  return res.json();
}

export async function fetchMetrics(): Promise<MetricsData> {
  const res = await fetchWithTimeout(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
}
