'use client';

interface Candidate {
    place_id: string;
    name: string;
    address: string;
    road_address?: string;
    provider: string;
}

interface CandidateListProps {
    candidates: Candidate[];
    selectedId: string | null;
    onSelect: (candidate: Candidate) => void;
}

export default function CandidateList({ candidates, selectedId, onSelect }: CandidateListProps) {
    return (
        <div className="candidate-list">
            {candidates.map(cand => (
                <div
                    key={cand.place_id}
                    className={`candidate-item ${selectedId === cand.place_id ? 'selected' : ''}`}
                    onClick={() => onSelect(cand)}
                >
                    <div className="candidate-name">{cand.name}</div>
                    <div className="candidate-address">{cand.road_address || cand.address}</div>
                    <div style={{ fontSize: '0.8rem', color: '#888' }}>{cand.provider}</div>
                </div>
            ))}
            {candidates.length === 0 && (
                <div style={{ padding: '1rem', color: '#888' }}>Search to see results</div>
            )}
        </div>
    );
}
