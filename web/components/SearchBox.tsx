'use client';

import { useState, useRef, useEffect } from 'react';
import { Search } from 'lucide-react';

interface SearchBoxProps {
    onSearch: (results: any[], error?: string) => void;
    onFocus: () => void;
    isExpanded: boolean; // Controls Hero vs Top Bar style
}

export default function SearchBox({ onSearch, onFocus, isExpanded }: SearchBoxProps) {
    const [query, setQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const abortControllerRef = useRef<AbortController | null>(null);

    const performSearch = async (searchTerm: string) => {
        if (!searchTerm.trim()) return;

        // Cancel previous request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        // Create new controller
        const controller = new AbortController();
        abortControllerRef.current = controller;

        setIsLoading(true);
        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
            const res = await fetch(`${baseUrl}/search/naver?query=${encodeURIComponent(searchTerm)}`, {
                signal: controller.signal
            });

            if (!res.ok) throw new Error('Search failed');

            const data = await res.json();
            onSearch(data); // Success

        } catch (err: any) {
            if (err.name === 'AbortError') return;
            console.error(err);
            onSearch([], '검색에 실패했습니다. 다시 시도해주세요.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        performSearch(query);
    };

    return (
        <div className={`search-container ${isExpanded ? 'active' : 'idle'}`}>
            <form
                onSubmit={handleSubmit}
                style={{ position: 'relative', maxWidth: '100%', width: '100%' }}
            >
                <input
                    type="text"
                    className="saas-input"
                    placeholder="가게 이름을 검색해 보세요 (예: 스타벅스 강남점)"
                    value={query}
                    onFocus={onFocus}
                    onChange={(e) => setQuery(e.target.value)}
                />

                <button
                    type="submit"
                    style={{
                        position: 'absolute',
                        right: '8px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: isLoading ? 'transparent' : '#2563eb',
                        color: isLoading ? '#999' : 'white',
                        border: 'none',
                        borderRadius: '50%',
                        width: '36px',
                        height: '36px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: isLoading ? 'default' : 'pointer'
                    }}
                    disabled={isLoading}
                >
                    {isLoading ? (
                        <div className="loading-spinner" style={{ width: '16px', height: '16px', borderTopColor: '#2563eb', border: '2px solid #eee' }}></div>
                    ) : (
                        <Search size={18} />
                    )}
                </button>
            </form>
        </div>
    );
}
