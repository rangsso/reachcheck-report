import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        const res = await fetch(`${BACKEND_URL}/report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            throw new Error(`Backend responded with ${res.status}`);
        }

        // The report endpoint returns HTML string
        const html = await res.text();
        return new NextResponse(html, {
            headers: { 'Content-Type': 'text/html' },
        });

    } catch (error) {
        console.error('Proxy Error (Report):', error);
        return NextResponse.json(
            { error: 'Failed to generate report', details: String(error) },
            { status: 500 }
        );
    }
}
