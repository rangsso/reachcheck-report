import type { Metadata } from 'next';
import './globals.css';
import Script from 'next/script';

export const metadata: Metadata = {
    title: 'ReachCheck Report',
    description: 'AI & Map Visibility Diagnostic Tool',
};

const KAKAO_KEY = process.env.NEXT_PUBLIC_KAKAO_MAP_KEY;

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <head>
                {/* Kakao Maps SDK */}
                <Script
                    src={`//dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_KEY}&libraries=services,clusterer&autoload=false`}
                    strategy="beforeInteractive"
                />
            </head>
            <body>{children}</body>
        </html>
    );
}
