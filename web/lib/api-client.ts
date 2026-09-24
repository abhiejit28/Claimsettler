// Central fetch wrapper. Every call targets the same-origin Route Handler
// proxy (app/api/backend/[...path]/route.ts), which forwards to the FastAPI
// backend and injects the adjuster bearer token server-side — components
// never talk to the backend origin directly and never see the token.

type ApiErrorBody = { detail?: string; message?: string }

class ApiClientError extends Error {
  status: number
  details?: unknown
  constructor(status: number, message: string, details?: unknown) {
    super(message)
    this.status = status
    this.details = details
  }
}

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/backend"

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    credentials: "include",
    cache: "no-store",
  })

  if (!res.ok) {
    let details: unknown
    try {
      details = (await res.json()) as ApiErrorBody
    } catch {
      /* body wasn't JSON */
    }
    const body = details as ApiErrorBody | undefined
    throw new ApiClientError(res.status, body?.detail ?? body?.message ?? res.statusText, details)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string, init?: RequestInit) => request<T>(path, { ...init, method: "GET" }),
  post: <T>(path: string, body?: unknown, init?: RequestInit) =>
    request<T>(path, { ...init, method: "POST", body: body ? JSON.stringify(body) : undefined }),
}

export { ApiClientError }
