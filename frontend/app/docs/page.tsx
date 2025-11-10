"use client";
import SwaggerUI from "swagger-ui-react";
import "swagger-ui-react/swagger-ui.css";

export default function DocsPage() {
  return (
    <div className="w-full">
      <SwaggerUI
        url="/v3/api-docs"
        docExpansion="none"
        displayRequestDuration={true}
        tryItOutEnabled={true}
      />
    </div>
  );
}
