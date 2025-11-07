import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function b64url(u8: Uint8Array) {
  let s = "";
  for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function middleware(req: NextRequest) {
  console.log('[Middleware] Running for:', req.nextUrl.pathname);
  
  const bytes = new Uint8Array(20);
  crypto.getRandomValues(bytes);
  const nonce = b64url(bytes);
  
  console.log('[Middleware] Generated nonce:', nonce);

  const reqHeaders = new Headers(req.headers);
  reqHeaders.set("x-csp-nonce", nonce);

  const res = NextResponse.next({ request: { headers: reqHeaders } });
  res.headers.set("X-CSP-Nonce", nonce);
  
  console.log('[Middleware] Set headers, returning response');
  return res;
}
