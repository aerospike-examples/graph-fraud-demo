'use client';

import 'swagger-ui-react/swagger-ui.css';
import NextDynamic from 'next/dynamic';

const SwaggerUI = NextDynamic(() => import('swagger-ui-react'), { ssr: false });

export default function DocsClient() {
    return (
        <div className="w-full">
            <SwaggerUI
                url="/v3/api-docs/fraud-detection"
                docExpansion="none"
                tryItOutEnabled
                displayRequestDuration
            />
        </div>
    );
}
