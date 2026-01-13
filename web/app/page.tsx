'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SearchBox from '@/components/SearchBox';
import CandidateList from '@/components/CandidateList';
import StickyCTA from '@/components/StickyCTA';

export default function Home() {
    const router = useRouter();
    const [view, setView] = useState<'IDLE' | 'SEARCHING' | 'RESULTS' | 'SELECTED' | 'GENERATING'>('IDLE');
    const [candidates, setCandidates] = useState<any[]>([]);
    const [selected, setSelected] = useState<any>(null);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    // Search Handler
    const handleSearch = (results: any[], error?: string) => {
        if (error) {
            setCandidates([]);
            setErrorMsg(error);
            setView('RESULTS'); // Show error state
            return;
        }

        setCandidates(results);
        setErrorMsg(null);
        setSelected(null);

        // Use timeout to allow smooth transition animation if needed
        setView(results.length > 0 ? 'RESULTS' : 'RESULTS');
    };

    // Card Selection
    const handleSelect = (cand: any | null) => {
        if (cand) {
            setSelected(cand);
            setView('SELECTED');
        } else {
            setSelected(null);
            setView('RESULTS');
        }
    };

    // Generate Report
    const handleGenerate = async () => {
        if (!selected) return;

        setView('GENERATING');

        try {
            // Include Naver specific fields
            const payload = {
                // Common fields
                store_name: selected.name,
                place_id: selected.place_id,

                // Naver specific fields (if available from source)
                address: selected.address,
                road_address: selected.road_address,
                tel: selected.phone || selected.tel,
                naver_link: selected.link,
                mapx: selected.mapx,
                mapy: selected.mapy,

                // Force Source to Naver to use Seed Logic in Collector
                source_type: 'naver_seed'
            };

            const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
            const res = await fetch(`${baseUrl}/report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!res.ok) throw new Error('Report generation failed');

            const html = await res.text();

            // Store HTML in localStorage to pass to result page (Simple MVP way)
            // Or just pass params. For large HTML, localStorage is better or re-fetch.
            // Let's use the existing flow: Result page likely re-fetches or we assume ID based?
            // Existing result page takes `html`? No, existing result page logic:
            // Actually, existing flow wasn't fully inspected for DATA PASSING.
            // Check previous `AnalyzeButton`: It performed POST, got HTML, then what?
            // It did: `localStorage.setItem('reportHtml', html); router.push('/result');`

            localStorage.setItem('reportHtml', html);
            router.push('/result');

        } catch (err) {
            console.error(err);
            alert('리포트 생성에 실패했습니다. 다시 시도해주세요.');
            setView('SELECTED'); // Revert state
        }
    };

    const isIdle = view === 'IDLE';

    return (
        <div className="container-saas">
            <header className="header">
                <div className="logo" onClick={() => window.location.reload()}>ReachCheck</div>
            </header>

            <main style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
                {/* Hero / Search Section */}
                <div className={`search-container ${isIdle ? 'idle' : 'active'}`}>
                    <div style={{ textAlign: isIdle ? 'center' : 'left', marginBottom: isIdle ? '20px' : '0' }}>
                        {isIdle && <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>매장 분석, 검색 한 번으로 끝.</h1>}
                    </div>

                    <SearchBox
                        onSearch={handleSearch}
                        onFocus={() => { if (isIdle) setView('SEARCHING'); }}
                        isExpanded={!isIdle}
                    />
                </div>

                {/* Content Area */}
                {!isIdle && (
                    <div style={{ flex: 1 }}>
                        <CandidateList
                            candidates={candidates}
                            selectedId={selected?.place_id || null}
                            onSelect={handleSelect}
                        />

                        {/* Empty/Error States */}
                        {candidates.length === 0 && !errorMsg && view !== 'SEARCHING' && (
                            <div className="state-message">검색 결과가 없습니다.</div>
                        )}

                        {errorMsg && (
                            <div className="state-message" style={{ color: '#ef4444' }}>{errorMsg}</div>
                        )}
                    </div>
                )}
            </main>

            {/* Sticky Footer CTA */}
            {view === 'SELECTED' && selected && (
                <StickyCTA
                    storeName={selected.name}
                    onGenerate={handleGenerate}
                    isLoading={false}
                />
            )}

            {view === 'GENERATING' && (
                <div className="loading-overlay" style={{ flexDirection: 'column', gap: '20px' }}>
                    <div className="loading-spinner" style={{ width: '40px', height: '40px', borderTopColor: '#2563eb', border: '4px solid #eee' }}></div>
                    <div>리포트를 생성하고 있습니다...</div>
                    <div style={{ fontSize: '0.9rem', color: '#666' }}>약 30초 정도 소요됩니다.</div>
                </div>
            )}
        </div>
    );
}
