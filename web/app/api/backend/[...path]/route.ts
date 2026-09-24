import { NextRequest, NextResponse } from "next/server"
import { getAdjusterToken } from "@/lib/cookies"

// Single catch-all proxy: the browser only ever talks same-origin to
// /api/backend/*, this Route Handler is the only thing that calls the
// FastAPI backend cross-origin (server-to-server, no browser CORS
// involved), and it's the one place the adjuster bearer token cookie is
// read and turned into an Authorization header. See lib/cookies.ts for why
// that cookie holds a raw bearer token rather than a backend-issued session.
const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000"

async function forward(request: NextRequest, path: string[]): Promise<NextResponse> {
  const token = await getAdjusterToken()
  const search = request.nextUrl.search
  const url = `${API_BASE_URL}/${path.join("/")}${search}`

  const headers = new Headers({ "Content-Type": "application/json" })
  if (token) headers.set("Authorization", `Bearer ${token}`)

  const hasBody = request.method !== "GET" && request.method !== "HEAD"
  const res = await fetch(url, {
    method: request.method,
    headers,
    body: hasBody ? await request.text() : undefined,
    cache: "no-store",
  })

  const body = await res.text()
  return new NextResponse(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
  })
}

type RouteParams = { params: Promise<{ path: string[] }> }

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return forward(request, path)
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const { path } = await params
  return forward(request, path)
}
