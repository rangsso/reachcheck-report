'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface StoreData {
    name: string;
    address: string;
    roadAddress?: string;
    tel?: string;
    link?: string;
    mapx?: string;
    mapy?: string;
}

interface AnalyzeButtonProps {
    selected: StoreData | null;
}

export default function AnalyzeButton({ selected }: AnalyzeButtonProps) {
    const [analyzing, setAnalyzing] = useState(false);
    const router = useRouter();

    const handleAnalyze = async () => {
        if (!selected) return;

        setAnalyzing(true);
        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
            const res = await fetch(`${baseUrl}/report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    store_name: selected.name,
                    address: selected.address,
                    road_address: selected.roadAddress,
                    tel: selected.tel,
                    naver_link: selected.link,
                    mapx: selected.mapx,
                    mapy: selected.mapy
                })
            });

            if (!res.ok) throw new Error('Analysis failed');

            const data = await res.json();

            // Navigate to result page with params
            // Using query params for stateless simple passing
            const params = new URLSearchParams({
                pdf: data.report_pdf_url,
                html: data.report_html_url,
                name: selected.name
            });

            router.push(`/result?${params.toString()}`);

        } catch (err: any) {
            console.error(err);
            alert('Analysis failed: ' + err.message);
            setAnalyzing(false);
        }
    };

    return (
        <div className="analyze-bar">
            <div>
                {selected ? (
                    <>
                        <strong>Selected:</strong> {selected.name}
                    </>
                ) : (
                    <span style={{ color: '#888' }}>Select a store from the list or map</span>
                )}
            </div>
            <button
                disabled={!selected || analyzing}
                onClick={handleAnalyze}
                style={{ background: '#16a34a' }}
            >
                {analyzing ? 'Analyzing...' : 'Generate Report'}
            </button>
            {analyzing && (
                <div className="loading-overlay" style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: 'rgba(255, 255, 255, 0.95)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '16px',
                    zIndex: 9999
                }}>
                    <div className="loading-spinner" style={{ width: '48px', height: '48px', border: '5px solid rgba(37, 99, 235, 0.2)', borderTopColor: '#2563eb' }}></div>
                    <div style={{ textAlign: 'center' }}>
                        <p style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1e293b', marginBottom: '8px' }}>리포트 생성 중...</p>
                        <p style={{ fontSize: '0.95rem', color: '#64748b' }}>약 5~10초 정도 소요됩니다.</p>
                    </div>
                </div>
            )}
        </div>
    );
}
