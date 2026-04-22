-- Supabase Dashboard > SQL Editor 에서 실행
-- 모든 테이블에 RLS 활성화 + anon read 정책

-- ── 읽기 전용 테이블 ─────────────────────────────────────

DO $$
DECLARE
  tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'raw_news', 'news_analyses', 'causal_chains',
    'indicator_gpr_daily_logs', 'indicator_ecos_daily_logs',
    'indicator_fred_daily_logs', 'indicator_kosis_monthly_logs',
    'cost_categories', 'consumer_items'
  ]
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format(
      'CREATE POLICY IF NOT EXISTS "anon_read" ON %I FOR SELECT TO anon USING (true)',
      tbl
    );
  END LOOP;
END $$;

-- ── admin 계정 role 설정 (사용자별 실행) ───────────────────
-- Supabase Dashboard > Authentication > Users > 해당 유저 > Edit
-- 또는 아래 SQL로 직접 설정 (user_id 교체 필요):
--
-- UPDATE auth.users
-- SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
-- WHERE email = 'admin@example.com';
