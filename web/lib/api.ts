// Typed client for the FastAPI backend. Keep in sync with api/schemas.py.

import { getAccessPassword } from "./access";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type CredentialStatus =
  | "valid"
  | "unverified"
  | "expiring_90"
  | "expiring_60"
  | "expiring_30"
  | "expired"
  | "verification_failed"
  | "excluded";

export type VerificationResult = "verified" | "not_found" | "excluded" | "mismatch" | "error";

export interface Verification {
  id: number;
  credential_id: number;
  checked_at: string;
  source: string;
  result: VerificationResult;
  details: Record<string, unknown>;
  evidence_path: string | null;
}

export interface Credential {
  id: number;
  associate_id: number;
  associate_name: string;
  manager_email: string;
  department: string;
  facility: string;
  credential_type: string;
  issuing_source: string;
  verify_method: string;
  lookup_url: string | null; // where a person checks a hand-verified credential
  number: string | null;
  issued_date: string | null;
  expires_date: string | null;
  status: CredentialStatus;
  days_left: number | null;
  last_verification: Verification | null;
  email_contacted: boolean;
  email_contact_count: number;
  last_email_contact_at: string | null;
  last_email_contact_channel: "email" | "outbox" | null;
}

export interface Associate {
  id: number;
  name: string;
  npi: string | null;
  role: string;
  department: string;
  facility: string;
  state: string;
  manager_email: string;
  worst_status: CredentialStatus | null;
  credential_count: number;
}

export interface AssociateDetail extends Associate {
  credentials: Credential[];
}

export interface Stats {
  associates: number;
  credentials: number;
  unverified: number;
  by_status: Record<CredentialStatus, number>;
  by_facility: { facility: string; total: number; by_status: Record<CredentialStatus, number> }[];
  timeline: { start: string; end: string; count: number }[];
}

export interface Filters {
  facilities: string[];
  departments: string[];
  managers: string[];
  demo_manager: string | null; // the manager with the largest team; the Manager view shows this team
  demo_team: string | null; // that team's department and facility
}

/** What a person saw when they looked a credential up at its source. */
export interface ManualVerification {
  result: "verified" | "not_found";
  number?: string;
  expires_date?: string;
  note?: string;
}

export interface VerifyAllResult {
  checked: number;
  by_result: Partial<Record<VerificationResult, number>>;
  skipped_manual?: number; // credentials verified by hand, left alone
}

/** Scope shared by the list, stats and verify-all endpoints. */
export interface Scope {
  manager?: string;
  department?: string;
  facility?: string;
}

export interface CredentialQuery extends Scope {
  status?: CredentialStatus[];
  expires_before?: string;
  limit?: number;
  offset?: number;
}

export interface AssociateQuery extends Scope {
  status?: CredentialStatus[];
  sort?: "urgency" | "name";
  limit?: number;
  offset?: number;
}

/** One page of a list endpoint; `total` is the match count before `limit` and `offset` (X-Total-Count). */
export interface Page<T> {
  items: T[];
  total: number;
}

export type AlertThreshold = "90" | "60" | "30" | "expired" | "excluded";

export interface Alert {
  id: number;
  credential_id: number;
  threshold: AlertThreshold;
  sent_to: string;
  sent_at: string;
  channel: string;
}

export interface AlertRunResult {
  sent: number;
  by_threshold: Partial<Record<AlertThreshold, number>>;
  by_channel?: { email: number; outbox: number }; // alert rows emailed vs left in the outbox
}

export interface CredentialEmailContact {
  credential_id: number;
  kind: "initial" | "follow_up";
  sent_to: string;
  sent_at: string;
  channel: "email" | "outbox";
}

export interface DailyRunResult {
  trigger: "scheduled" | "manual";
  started_at: string;
  finished_at: string;
  checked: number;
  by_result: Partial<Record<VerificationResult, number>>;
  alerts: AlertRunResult | null; // null when the sweep was skipped
  alerts_skipped: string | null;
}

export interface DailyJobStatus {
  enabled: boolean;
  next_run_at: string | null;
  running: boolean;
  last_run: DailyRunResult | null;
}

export interface AccessStatus {
  required: boolean;
  granted: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Params = Record<string, string | number | string[] | undefined>;

function url(path: string, params: Params = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === "") continue;
    for (const v of Array.isArray(value) ? value : [value]) search.append(key, String(v));
  }
  const query = search.toString();
  return `${API_URL}/api${path}${query ? `?${query}` : ""}`;
}

async function send(
  path: string,
  params?: Params,
  method: "GET" | "POST" = "GET",
  body?: unknown,
): Promise<Response> {
  // The password header is only sent when one is set, so an open API gets no CORS preflight.
  const password = getAccessPassword();
  const headers: Record<string, string> = {};
  if (password) headers["X-Access-Password"] = password;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url(path, params), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.ok) return res;
  let message = `${method} ${path} failed (${res.status})`;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
      message += `: ${body.detail}`;
    }
  } catch {
    // Body was not JSON; keep the status-only message.
  }
  throw new ApiError(message, res.status);
}

async function request<T>(path: string, params?: Params, method: "GET" | "POST" = "GET"): Promise<T> {
  return (await (await send(path, params, method)).json()) as T;
}

async function page<T>(path: string, params: Params): Promise<Page<T>> {
  const res = await send(path, params);
  const items = (await res.json()) as T[];
  const header = res.headers.get("X-Total-Count");
  return { items, total: header === null ? items.length : Number(header) };
}

/** Every matching credential, fetched in pages of the backend's maximum `limit`. */
async function allCredentials(params: Omit<CredentialQuery, "limit" | "offset"> = {}): Promise<Credential[]> {
  const PAGE = 2000;
  const items: Credential[] = [];
  for (;;) {
    const next = await page<Credential>("/credentials", { ...params, limit: PAGE, offset: items.length });
    items.push(...next.items);
    if (next.items.length === 0 || items.length >= next.total) return items;
  }
}

/** Link to the evidence PDF for one verification. */
export function evidenceUrl(verificationId: number): string {
  // A plain link cannot send a header, so the password travels as a query parameter.
  return url(`/evidence/${verificationId}.pdf`, { access: getAccessPassword() });
}

export const api = {
  health: () => request<{ status: "ok" }>("/health"),
  access: () => request<AccessStatus>("/access"),
  stats: (scope: Scope = {}) => request<Stats>("/stats", { ...scope }),
  filters: () => request<Filters>("/filters"),
  credentials: (params: CredentialQuery = {}) => request<Credential[]>("/credentials", { ...params }),
  credentialsPage: (params: CredentialQuery = {}) => page<Credential>("/credentials", { ...params }),
  associates: (params: AssociateQuery = {}) => request<Associate[]>("/associates", { ...params }),
  associatesPage: (params: AssociateQuery = {}) => page<Associate>("/associates", { ...params }),
  associate: (id: number) => request<AssociateDetail>(`/associates/${id}`),
  verifyCredential: (id: number) => request<Verification>(`/verify/credential/${id}`, undefined, "POST"),
  recordManualVerification: async (id: number, body: ManualVerification) =>
    (await (await send(`/verify/credential/${id}/manual`, undefined, "POST", body)).json()) as Verification,
  verifyAssociate: (id: number) => request<Verification[]>(`/verify/associate/${id}`, undefined, "POST"),
  verifyAll: (scope: Scope = {}) => request<VerifyAllResult>("/verify/all", { ...scope }, "POST"),
  allCredentials,
  alerts: () => request<Alert[]>("/alerts"),
  runAlerts: () => request<AlertRunResult>("/alerts/run", undefined, "POST"),
  emailCredentialContact: (id: number) =>
    request<CredentialEmailContact>(`/alerts/credential/${id}/email`, undefined, "POST"),
  dailyJob: () => request<DailyJobStatus>("/jobs/daily"),
  runDailyJob: () => request<DailyRunResult>("/jobs/daily/run", undefined, "POST"),
};
