"use client";

import { useEffect, useState } from "react";

export function useNonce() {
  const [nonce, setNonce] = useState<string | undefined>(undefined);

  useEffect(() => {
    const cookies = document.cookie.split("; ");
    const nonceCookie = cookies.find((c) => c.startsWith("csp-nonce="));
    if (nonceCookie) {
      setNonce(nonceCookie.split("=")[1]);
    }
  }, []);

  return nonce;
}
