'use client';

import { Play } from 'lucide-react';

interface StickyCTAProps {
    storeName: string;
    onGenerate: () => void;
    isLoading: boolean;
}

export default function StickyCTA({ storeName, onGenerate, isLoading }: StickyCTAProps) {
    return (
        <div className="sticky-cta">
            <div className="cta-inner">
                <div className="cta-summary">
                    선택된 매장: <span style={{ color: '#2563eb' }}>{storeName}</span>
                </div>
                <button
                    className="cta-button"
                    onClick={onGenerate}
                    disabled={isLoading}
                >
                    {isLoading ? (
                        <>
                            <div className="loading-spinner" style={{ width: '16px', height: '16px' }}></div>
                            분석 중...
                        </>
                    ) : (
                        <>
                            <Play size={18} fill="currentColor" />
                            리포트 생성하기
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
