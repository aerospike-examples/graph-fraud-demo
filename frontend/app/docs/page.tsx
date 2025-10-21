"use client";

import { useEffect, useRef, useState } from "react";

const DocsPage = () => {
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const [height, setHeight] = useState("100vh");

  useEffect(() => {
    const iframe = frameRef.current;
    if (!iframe) return;
    const onLoad = () => {
      try {
        const doc = iframe.contentWindow?.document;
        const h =
          doc?.documentElement?.scrollHeight || doc?.body?.scrollHeight || 0;
        if (h && h > 400) setHeight(`${h}px`);
        else setHeight("100vh");
      } catch (e) {
        setHeight("100vh");
      }
    };
    iframe.addEventListener("load", onLoad);
    return () => iframe.removeEventListener("load", onLoad);
  }, []);

  return (
    <iframe
      src="/swagger-ui/index.html"
      className="iframe"
      style={{ width: "100%", height }}
      ref={frameRef}
    />
  );
};

export default DocsPage;
