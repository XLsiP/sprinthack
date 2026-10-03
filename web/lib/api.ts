// Typed client for the FastAPI backend. Keep in sync with api/schemas.py.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type CredentialStatus =
  | "valid"
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
  department: string;
  facility: string;
  credential_type: string;
  issuing_source: string;
  verify_method: string;
  number: string | null;
  issued_date: string | null;
  expires_date: string | null;
  status: CredentialStatus;
  days_left: number | null;
  last_verification: Verification | null;
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
  timeline: { month: string; count: number }[];
}

export interface Filters {
  facilities: string[];
  departments: string[];
  managers: string[];
}

export interface VerifyAllResult {
  checked: number;
  by_result: Partial<Record<VerificationResult, number>>;
}

/** Scope shared by the list, stats and verify-all endpoints. */
export interface Scope {
  manager?: string;
  department?: string;
  facility?: string;
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

async function request<T>(path: string, params?: Params, method: "GET" | "POST" = "GET"): Promise<T> {
  const res = await fetch(url(path, params), { method });
  if (!res.ok) throw new Error(`${method} ${path} failed (${res.status})`);
  return (await res.json()) as T;
}

export const api = {
  stats: (scope: Scope = {}) => request<Stats>("/stats", { ...scope }),
  filters: () => request<Filters>("/filters"),
  credentials: (params: Scope & { status?: CredentialStatus[]; expires_before?: string; limit?: number } = {}) =>
    request<Credential[]>("/credentials", { ...params }),
  associates: (params: Scope & { status?: CredentialStatus; limit?: number } = {}) =>
    request<Associate[]>("/associates", { ...params }),
  associate: (id: number) => request<AssociateDetail>(`/associates/${id}`),
  verifyCredential: (id: number) => request<Verification>(`/verify/credential/${id}`, undefined, "POST"),
  verifyAssociate: (id: number) => request<Verification[]>(`/verify/associate/${id}`, undefined, "POST"),
  verifyAll: (scope: Scope = {}) => request<VerifyAllResult>("/verify/all", { ...scope }, "POST"),
};
