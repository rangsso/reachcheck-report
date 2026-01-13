'use client';

import { useState } from 'react';

interface SearchBoxProps {
    onSearch: (candidates: any[]) => void;
    setLoading: (loading: boolean) => void;
}

export default function SearchBox({ onSearch, setLoading }: SearchBoxProps) {
    const [query, setQuery] = useState('');
    const [isSearching, setIsSearching] = useState(false);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query) return;

        setLoading(true);
        setIsSearching(true);
        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
            const res = await fetch(`${baseUrl}/search/naver?query=${encodeURIComponent(query)}`);
            const data = await res.json();
            onSearch(data);
        } catch (err) {
            console.error(err);
            alert('Search failed');
        } finally {
            setLoading(false);
            setIsSearching(false);
        }
    };

    return (
        <form className="search-section" onSubmit={handleSearch}>
            <input
                type="text"
                placeholder="Search store name (e.g., Starbucks Gangnam)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" disabled={isSearching}>
                {isSearching ? 'Searching...' : 'Search'}
            </button>
        </form>
    );
}
