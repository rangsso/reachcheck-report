'use client';

import { Check } from 'lucide-react';

interface Candidate {
    place_id: string;
    name: string;
    address: string;
    road_address?: string;
    category?: string;
    tel?: string;
    provider: string;
    link?: string;
}

interface CandidateListProps {
    candidates: Candidate[];
    selectedId: string | null;
    onSelect: (candidate: Candidate | null) => void;
}

export default function CandidateList({ candidates, selectedId, onSelect }: CandidateListProps) {
    if (candidates.length === 0) return null;

    return (
        <div className="result-grid">
            {candidates.map(cand => {
                const isSelected = selectedId === cand.place_id;
                return (
                    <div
                        key={cand.place_id}
                        className={`saas-card ${isSelected ? 'selected' : ''}`}
                        onClick={() => onSelect(isSelected ? null : cand)} // Toggle selection
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div className="card-title">{cand.name}</div>
                            {isSelected && <Check size={20} color="#2563eb" />}
                        </div>

                        <div className="card-sub">{cand.road_address || cand.address}</div>

                        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                            <span className="card-badge">{cand.category || '일반 매장'}</span>
                            {cand.tel && <span className="card-badge">{cand.tel}</span>}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
