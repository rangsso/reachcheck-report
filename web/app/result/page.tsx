'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense } from 'react';

function ResultContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const pdfUrl = searchParams.get('pdf');
    const htmlUrl = searchParams.get('html');
    const name = searchParams.get('name');

    if (!pdfUrl || !htmlUrl) {
        return <div>Invalid result parameters. <button onClick={() => router.push('/')}>Go Home</button></div>;
    }

    return (
        <div className="container result-view">
            <header>
                <h1>ReachCheck Report</h1>
                <p>Analysis Complete for {name}</p>
            </header>

            <div className="report-links">
                <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="button">
                    Download PDF
                </a>
                <a href={htmlUrl} target="_blank" rel="noopener noreferrer" className="button">
                    Open HTML
                </a>
                <button onClick={() => router.push('/')}>Start Over</button>
            </div>

            <iframe
                src={htmlUrl}
                className="report-frame"
                title="Report Preview"
            />
        </div>
    );
}

export default function ResultPage() {
    return (
        <Suspense fallback={<div>Loading result...</div>}>
            <ResultContent />
        </Suspense>
    );
}
