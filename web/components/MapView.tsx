'use client';

import { useEffect, useRef } from 'react';

declare global {
    interface Window {
        kakao: any;
    }
}

interface MapViewProps {
    candidates: any[];
    selectedId: string | null;
    onSelect: (cand: any) => void;
}

export default function MapView({ candidates, selectedId, onSelect }: MapViewProps) {
    const mapRef = useRef<any>(null);
    const markersRef = useRef<any[]>([]);

    // Initialize Map
    useEffect(() => {
        // Check if script is loaded
        if (!window.kakao || !window.kakao.maps) {
            // Retry logic or assume script is loading in layout
            const check = setInterval(() => {
                if (window.kakao && window.kakao.maps) {
                    clearInterval(check);
                    initMap();
                }
            }, 100);
            return () => clearInterval(check);
        }
        initMap();

        function initMap() {
            if (mapRef.current) return;

            window.kakao.maps.load(() => {
                const container = document.getElementById('kakao-map');
                const options = {
                    center: new window.kakao.maps.LatLng(37.566826, 126.9786567),
                    level: 3
                };
                mapRef.current = new window.kakao.maps.Map(container, options);
            });
        }
    }, []);

    // Update Markers
    useEffect(() => {
        if (!mapRef.current || !window.kakao || !window.kakao.maps) return;

        // Clear existing markers
        markersRef.current.forEach(m => m.setMap(null));
        markersRef.current = [];

        if (candidates.length > 0) {
            const bounds = new window.kakao.maps.LatLngBounds();

            candidates.forEach(cand => {
                const position = new window.kakao.maps.LatLng(cand.lat, cand.lng);
                const marker = new window.kakao.maps.Marker({
                    position: position,
                    map: mapRef.current
                });

                window.kakao.maps.event.addListener(marker, 'click', () => {
                    onSelect(cand);
                });

                markersRef.current.push(marker);
                bounds.extend(position);
            });

            mapRef.current.setBounds(bounds);
        }
    }, [candidates]);

    // Pan to selected
    useEffect(() => {
        if (!mapRef.current || !selectedId || !window.kakao) return;

        const selected = candidates.find(c => c.place_id === selectedId);
        if (selected) {
            const moveLatLon = new window.kakao.maps.LatLng(selected.lat, selected.lng);
            mapRef.current.panTo(moveLatLon);
        }
    }, [selectedId, candidates]);

    return (
        <div className="map-container">
            <div id="kakao-map"></div>
        </div>
    );
}
