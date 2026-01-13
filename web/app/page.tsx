'use client';

import { useState } from 'react';
import SearchBox from '@/components/SearchBox';
import CandidateList from '@/components/CandidateList';
import MapView from '@/components/MapView';
import AnalyzeButton from '@/components/AnalyzeButton';

export default function Home() {
    const [candidates, setCandidates] = useState<any[]>([]);
    const [selected, setSelected] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const handleSearch = (results: any[]) => {
        setCandidates(results);
        if (results.length > 0) {
            setSelected(null);
        }
    };

    const handleSelect = (cand: any) => {
        setSelected(cand);
    };

    return (
        <div className="container">
            <header>
                <h1>ReachCheck E2E Demo</h1>
            </header>

            <SearchBox onSearch={handleSearch} setLoading={setLoading} />

            <div className="content-grid">
                <CandidateList
                    candidates={candidates}
                    selectedId={selected?.place_id || null}
                    onSelect={handleSelect}
                />
                <MapView
                    candidates={candidates}
                    selectedId={selected?.place_id || null}
                    onSelect={handleSelect}
                />
            </div>

            <AnalyzeButton selected={selected} />
        </div>
    );
}
