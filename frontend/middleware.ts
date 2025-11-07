import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function b64url(u8: Uint8Array) {
  let s = "";
  for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function middleware(req: NextRequest) {
  const bytes = new Uint8Array(20);
  crypto.getRandomValues(bytes);
  const nonce = b64url(bytes);

  const reqHeaders = new Headers(req.headers);
  reqHeaders.set("x-csp-nonce", nonce);

  const res = NextResponse.next({ request: { headers: reqHeaders } });

  res.headers.set("X-CSP-Nonce", nonce);

  return res;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|api|swagger-ui|v3/api-docs).*)",
  ],
};