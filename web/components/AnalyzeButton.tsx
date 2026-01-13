'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface AnalyzeButtonProps {
    selected: any;
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
                    place_id: selected.place_id,
                    store_name: selected.name
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
                <div className="loading-overlay">
                    <div>
                        <p>Analyzing {selected?.name}...</p>
                        <small>Generating Snapshots & Report</small>
                    </div>
                </div>
            )}
        </div>
    );
}
