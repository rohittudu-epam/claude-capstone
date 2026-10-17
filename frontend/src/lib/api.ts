import { logger } from "@/lib/logger";
import type {
  Graph,
  NoteLink,
  Note,
  NotePayload,
  NoteSummary,
  Page,
  SearchHit,
  Session,
  Suggestion,
  Tag,
  User,
} from "@/lib/types";

export interface FieldError {
  field: string;
  message: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly correlationId: string | null = null,
    public readonly fieldErrors: FieldError[] = [],
  ) {
    super(detail);
    this.name = "ApiError";
  }

  /** The server could not be reached at all (offline, proxy down). */
  get isNetwork(): boolean {
    return this.status === 0;
  }
}

type Listener = () => void;
const expiredListeners = new Set<Listener>();

/** Called when a request failed with 401 and the session could not be refreshed. */
export function onSessionExpired(listener: Listener): () => void {
  expiredListeners.add(listener);
  return () => expiredListeners.delete(listener);
}

let refreshInFlight: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  try {
    const response = await fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" });
    return response.ok;
  } catch {
    return false;
  }
}

/** Concurrent 401s share one refresh, because the server rotates (and revokes) the refresh token on use. */
function refreshOnce(): Promise<boolean> {
  refreshInFlight ??= refreshSession().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

function isAuthEndpoint(path: string): boolean {
  return path.startsWith("/api/auth/");
}

async function send(method: string, path: string, body?: unknown): Promise<Response> {
  try {
    return await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }
}

async function toError(response: Response, path: string): Promise<ApiError> {
  let detail = response.statusText || "Request failed";
  let correlationId = response.headers.get("x-correlation-id");
  let fieldErrors: FieldError[] = [];
  try {
    const payload = (await response.json()) as { detail?: unknown; errors?: FieldError[]; correlation_id?: string };
    if (typeof payload.detail === "string") detail = payload.detail;
    if (Array.isArray(payload.errors)) fieldErrors = payload.errors;
    correlationId = payload.correlation_id ?? correlationId;
  } catch {
    // Non-JSON error body (for example a proxy error page): keep the status text.
  }
  logger.error("api request failed", { status: response.status, correlationId, path: path.split("?")[0] });
  return new ApiError(response.status, detail, correlationId, fieldErrors);
}

export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response = await send(method, path, body);

  if (response.status === 401 && !isAuthEndpoint(path)) {
    if (await refreshOnce()) {
      response = await send(method, path, body);
    }
    if (response.status === 401) {
      expiredListeners.forEach((listener) => listener());
      throw await toError(response, path);
    }
  }

  if (!response.ok) throw await toError(response, path);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function query(params: Record<string, string | number | string[] | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || (Array.isArray(value) && value.length === 0)) continue;
    search.set(key, Array.isArray(value) ? value.join(",") : String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export interface ListParams {
  limit?: number;
  offset?: number;
  tags?: string[];
}

export const api = {
  me: () => request<User>("GET", "/api/auth/me"),
  register: (body: { email: string; password: string }) => request<User>("POST", "/api/auth/register", body),
  login: (body: { email: string; password: string }) => request<Session>("POST", "/api/auth/login", body),
  logout: () => request<void>("POST", "/api/auth/logout"),

  listNotes: (params: ListParams) => request<Page<NoteSummary>>("GET", `/api/notes${query({ ...params })}`),
  searchNotes: (q: string, params: ListParams) =>
    request<Page<SearchHit>>("GET", `/api/notes/search${query({ q, ...params })}`),
  getNote: (id: string) => request<Note>("GET", `/api/notes/${id}`),
  createNote: (body: NotePayload) => request<Note>("POST", "/api/notes", body),
  updateNote: (id: string, body: NotePayload) => request<Note>("PUT", `/api/notes/${id}`, body),
  deleteNote: (id: string) => request<void>("DELETE", `/api/notes/${id}`),
  listTags: () => request<Tag[]>("GET", "/api/tags"),

  listSuggestions: (params: { limit?: number; offset?: number; noteId?: string } = {}) =>
    request<Page<Suggestion>>(
      "GET",
      `/api/suggestions${query({ limit: params.limit, offset: params.offset, note_id: params.noteId })}`,
    ),
  acceptSuggestion: (id: string) => request<NoteLink>("POST", `/api/suggestions/${id}/accept`),
  rejectSuggestion: (id: string) => request<void>("POST", `/api/suggestions/${id}/reject`),
  listLinks: (params: { noteId?: string; limit?: number } = {}) =>
    request<Page<NoteLink>>("GET", `/api/links${query({ note_id: params.noteId, limit: params.limit })}`),

  getGraph: (tags: string[]) => request<Graph>("GET", `/api/graph${query({ tags })}`),
};
