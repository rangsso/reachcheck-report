'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';

function ResultContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [htmlContent, setHtmlContent] = useState<string | null>(null);

    useEffect(() => {
        // Try to get from Params first (legacy), then LocalStorage
        const htmlParam = searchParams.get('html');
        if (htmlParam) {
            setHtmlContent(htmlParam);
        } else {
            const storedHtml = localStorage.getItem('reportHtml');
            if (storedHtml) {
                setHtmlContent(storedHtml);
            }
        }
    }, [searchParams]);

    if (!htmlContent) {
        return (
            <div className="container-saas" style={{ textAlign: 'center', marginTop: '100px' }}>
                <div style={{ marginBottom: '20px', color: '#ef4444' }}>리포트 데이터를 찾을 수 없습니다.</div>
                <button className="cta-button" onClick={() => router.push('/')}>홈으로 돌아가기</button>
            </div>
        );
    }

    const handlePrint = () => {
        const iframe = document.querySelector('iframe.report-frame') as HTMLIFrameElement;
        if (iframe && iframe.contentWindow) {
            iframe.contentWindow.print();
        } else {
            alert('리포트를 로딩 중입니다. 잠시 후 다시 시도해주세요.');
        }
    };

    // Robust content detection
    let finalSrc = "";
    let isRawHtml = false;

    // Check if it's a URL
    if (htmlContent.trim().startsWith('http') || htmlContent.trim().startsWith('/')) {
        finalSrc = htmlContent;
    }
    // Check if it's JSON text (The potential bug source)
    else if (htmlContent.trim().startsWith('{')) {
        try {
            const parsed = JSON.parse(htmlContent);
            if (parsed.html_content) {
                finalSrc = parsed.html_content;
                isRawHtml = true;
            } else if (parsed.report_html_url) {
                finalSrc = parsed.report_html_url;
            } else {
                // Fallback: If JSON but no known keys, just render it (debug) but warn?
                // Or better, don't render raw JSON to user.
                console.warn("Unknown JSON format in report view");
                finalSrc = "Invalid report format.";
                isRawHtml = true;
            }
        } catch (e) {
            // Not valid JSON, treat as raw HTML string
            finalSrc = htmlContent;
            isRawHtml = true;
        }
    } else {
        // Plain string (HTML)
        finalSrc = htmlContent;
        isRawHtml = true;
    }

    return (
        <div className="container-saas report-view-container">
            <header className="header" style={{ justifyContent: 'space-between', marginBottom: '0' }}>
                <div className="logo" onClick={() => router.push('/')}>ReachCheck</div>
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={handlePrint} className="cta-button" style={{ height: '36px', fontSize: '0.9rem', padding: '0 16px', background: '#fff', border: '1px solid #e2e8f0', color: '#333' }}>
                        PDF 저장/인쇄
                    </button>
                    <button onClick={() => router.push('/')} className="cta-button" style={{ height: '36px', fontSize: '0.9rem', padding: '0 16px' }}>
                        종료
                    </button>
                </div>
            </header>

            <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '16px', marginTop: '20px' }}>
                {isRawHtml ? (
                    <iframe
                        srcDoc={finalSrc}
                        className="report-frame"
                        title="Report Preview"
                        style={{ height: 'calc(100vh - 150px)' }}
                    />
                ) : (
                    <iframe
                        src={finalSrc}
                        className="report-frame"
                        title="Report Preview"
                        style={{ height: 'calc(100vh - 150px)' }}
                    />
                )}
            </div>
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
