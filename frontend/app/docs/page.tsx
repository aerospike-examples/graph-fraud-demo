"use client";

import { useEffect, useRef, useState } from "react";

const DocsPage = () => {
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const [heightPx, setHeightPx] = useState(800);

  useEffect(() => {
    const iframe = frameRef.current;
    if (!iframe) return;
    const onLoad = () => {
      try {
        const doc = iframe.contentWindow?.document;
        const h =
          doc?.documentElement?.scrollHeight || doc?.body?.scrollHeight || 0;
        if (h && h > 400) setHeightPx(h);
        else setHeightPx(800);
      } catch (e) {
        setHeightPx(800);
      }
    };
    iframe.addEventListener("load", onLoad);
    return () => iframe.removeEventListener("load", onLoad);
  }, []);

  return (
    <iframe
      src="/swagger-ui/index.html"
      className="w-full"
      height={heightPx}
      ref={frameRef}
    />
  );
};

export default DocsPage;
