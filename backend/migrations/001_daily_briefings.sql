-- daily_briefings: 일별 물가 브리핑 저장 테이블
-- LLM3(briefing_main.py)가 매일 upsert, 백엔드 /api/v1/briefing/today가 공개 조회

CREATE TABLE IF NOT EXISTS daily_briefings (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    briefing_date   date NOT NULL,
    headline        text NOT NULL,
    overview        text NOT NULL DEFAULT '',
    items           jsonb NOT NULL DEFAULT '[]',
    overall_risk    text NOT NULL DEFAULT 'medium'
                        CHECK (overall_risk IN ('low', 'medium', 'high')),
    consumer_tip    text,
    indicators      jsonb,
    source_count    int NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS daily_briefings_date_idx
    ON daily_briefings (briefing_date);

-- 공개 조회 허용 (RLS 없이 anon 읽기)
ALTER TABLE daily_briefings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read" ON daily_briefings
    FOR SELECT USING (true);
