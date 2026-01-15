
lines = open('reachcheck_mvp/templates/report.html').readlines()
part1 = lines[:333]
# We want to skip the middle mess.
# Based on my analysis, the 'good' part resumes at line 518 (index 517).
part3 = lines[517:]

new_content = """        }
    </style>
</head>

<body>

    <!-- Print Root Wrapper for Strict A4 Layout -->
    <div class="print-root">

        <!-- Page 1: Consolidated Summary -->
        <div class="page">
            <div class="header">
                <h1>[{{ data.store.name }}] AI·검색 노출 진단 리포트</h1>
                <span class="date">{{ data.date }}</span>
            </div>

            <!-- 1. Horizontal Health Banner -->
            <div class="health-banner">
                <div class="health-banner-left">
                    <span class="health-title">사장님의 매장 건강 점수</span>
                    <span class="health-score">{{ data.analysis.reachcheck_score }}점</span>
                </div>
                <div class="health-banner-right">
                    상위 {{ 100 - data.analysis.reachcheck_score }}% 수준 (매우 건강함)
                </div>
            </div>

            <!-- 2. Prescription & Action Link (Split Row) -->
            <div class="split-row">
                <!-- Left: Prescription -->
                <div class="split-box" style="flex: 1.2;">
                    <div class="box-header">
                        <span>⚕️ 클리닉 처방전</span>
                    </div>
                    <div class="prescription-content">
                        <span style="font-size: 24px;">💊</span>
                        <div class="prescription-text">
                            "{{ data.review_insights.prescription if data.review_insights and data.review_insights.prescription else '진단 데이터가 충분하지 않습니다.' }}"
                        </div>
                    </div>
                </div>

                <!-- Right: Action Plan (Today Action) -->
                {% if data.action_summary %}
                <div class="split-box" style="flex: 1; background: #fff5f5; border-color: #feb2b2;">
                    <div class="box-header" style="border-color: #fed7d7;">
                        <span style="color: #c53030;">🚨 오늘 바로 해결하기</span>
                    </div>
                    <div class="action-content">
                        <div class="warning-msg">{{ data.action_summary.warning }}</div>
                        <div class="solution-msg">🚀 {{ data.action_summary.action }}</div>
                        <div style="font-size: 10px; color: #718096; margin-top: 2px;">
                            효과: {{ data.action_summary.benefit }}
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>

            <!-- 3. Diagnostic Summary Text -->
            <div class="section">
                <div class="section-title">진단 요약</div>
                <div class="compact-summary">
                    <p>{{ data.analysis.map_summary }}</p>
                    <div style="height: 4px;"></div>
                    <p>{{ data.analysis.ai_summary }}</p>
                </div>
            </div>

            <!-- 4. Map Channel Status -->
            <div class="section">
                <div class="section-title">지도 채널 등록 현황</div>
                <div class="grid-3">
                    {% for channel in data.analysis.map_statuses %}
                    <div class="mini-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <h4>{{ channel.channel_name }}</h4>
                            <span class="status-badge bg-{{ channel.color.value }}">
                                {{ '등록됨' if channel.is_registered else '미등록' }}
                            </span>
                        </div>
                        <p>{{ channel.status_text }}</p>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- 5. Compact Provenance Table -->
            <div class="section" style="flex-grow: 1;">
                <div class="section-title">데이터 출처 및 정합성 (Consistency Check)</div>
                <table class="compact-table">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="width: 15%">항목 (Field)</th>
                            <th style="width: 25%">Standard (Naver)</th>
                            <th style="width: 20%">Kakao</th>
                            <th style="width: 20%">Google</th>
                            <th style="width: 20%">상태 (Status)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if data.analysis.field_provenance and data.analysis.field_provenance.fields %}
                        {% for key, val in data.analysis.field_provenance.fields.items() %}
                        {% if key != 'category' %}
                        <tr>
                            <td style="font-weight: 600; color: #475569;">{{ key|capitalize }}</td>
                            <td>{{ val.standard }}</td>
                            <td>{{ val.sources.kakao or '-' }}</td>
                            <td>{{ val.sources.google or '-' }}</td>
                            <td>
                                {% set ns = namespace(status='Unknown', color='black') %}
                                {% for cr in data.analysis.consistency_results %}
                                {% if cr.field_name|lower == key|lower %}
                                {% set ns.status = cr.status %}
                                {% set ns.color = 'text-match' if cr.status == 'Match' else 'text-mismatch' %}
                                {% endif %}
                                {% endfor %}
                                <span class="{{ ns.color }}">{{ ns.status }}</span>
                            </td>
                        </tr>
                        {% endif %}
                        {% endfor %}
                        {% endif %}
                    </tbody>
                </table>
            </div>

            <div class="footer">Page 1 / 4 • ReachCheck Analysis</div>
        </div>

        <!-- Page 2: AI Responses -->
        <div class="page">
            <div class="header">
                <h1>AI가 바라본 우리 가게</h1>
                <span class="date">{{ data.date }}</span>
            </div>

            <div class="section">
                <div class="section-title">AI 엔진별 상세 답변 분석</div>
                <p style="font-size: 13px; color: #64748b; margin-bottom: 20px;">
                    실제 AI에게 우리 매장에 대해 물어봤을 때의 답변입니다. (실제 데이터 기반)
                </p>
                {% for engine, responses in data.analysis.ai_responses.items() %}
"""

with open('reachcheck_mvp/templates/report.html', 'w') as f:
    f.writelines(part1)
    f.write(new_content)
    f.writelines(part3)
