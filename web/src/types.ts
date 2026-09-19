export interface Mandate {
  mandate_id: string;
  user_id: string;
  agent_id: string;
  merchant_slug: string;
  spend_cap_paise: number;
  valid_from: number;
  valid_until: number;
  status: 'active' | 'revoked' | 'expired';
}

export interface AgentAction {
  seq: number;
  action: 'search' | 'select' | 'confirm' | 'pay';
  ts: number;
  payload: Record<string, unknown>;
}

export interface Fulfilment {
  order_id: string;
  delivered: boolean;
  delivered_ts: number | null;
  amount_paise: number;
}

export interface CheckResult {
  id: number;
  name: string;
  engine: 'cedar' | 'python';
  passed: boolean;
  detail: string;
}

export interface Dispute {
  dispute_id: string;
  mandate_id: string;
  merchant_slug: string;
  amount_paise: number;
  txn_ts: number;
  actions: AgentAction[];
  fulfilment: Fulfilment;
  status: 'received' | 'contest' | 'escalate' | 'accept';
  checks: CheckResult[];
  confidence: number;
  narrative: string | null;
  grounded: boolean;
  escalation_reason: string | null;
}

export interface AuditEntry {
  ts: number;
  actor: string;
  event: string;
  from_status: string;
  to_status: string;
  detail: string;
}

export interface MetricsData {
  precision: number;
  recall: number;
  f1: number;
  confusion: {
    tp: number;
    fp: number;
    tn: number;
    fn: number;
  };
  n: number;
}
