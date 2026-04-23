const { createClient } = require('@supabase/supabase-js');
const SUPABASE_URL = "https://ijhgmemuzeujpvdlywjn.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlqaGdtZW11emV1anB2ZGx5d2puIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU2MjY4MzEsImV4cCI6MjA5MTIwMjgzMX0.BPRAtx51G0ro0QZGC3qW63c7Y1jbSzFC7CuVr6nSU7k";

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function run() {
  console.log('--- DB Check ---');
  // GPR
  let { data: gpr } = await supabase.from('indicator_gpr_monthly_logs').select('*').order('AI_GPR_Index', { ascending: false }).limit(10);
  console.log('AI_GPR_Index top 10:', gpr?.map(r => `${r.reference_date}: ${r.AI_GPR_Index}`));
  let { data: gprAll } = await supabase.from('indicator_gpr_monthly_logs').select('AI_GPR_Index');
  if (gprAll && gprAll.length > 0) {
      let gprAvg = gprAll.reduce((a, b) => a + (b.AI_GPR_Index || 0), 0) / gprAll.length;
      console.log('AI_GPR_Index avg:', gprAvg);
  }

  // ECOS
  let { data: ecos } = await supabase.from('indicator_ecos_monthly_logs').select('krw_usd_rate, reference_date').order('krw_usd_rate', { ascending: false }).limit(10);
  console.log('krw_usd_rate top 10:', ecos?.map(r => `${r.reference_date}: ${r.krw_usd_rate}`));

  // FRED WTI
  let { data: fredWti } = await supabase.from('indicator_fred_monthly_logs').select('fred_wti, reference_month').order('fred_wti', { ascending: false }).limit(10);
  console.log('fred_wti top 10:', fredWti?.map(r => `${r.reference_month}: ${r.fred_wti}`));

  // FRED Treasury
  let { data: fredFed } = await supabase.from('indicator_fred_monthly_logs').select('fred_treasury_10y, reference_month').order('fred_treasury_10y', { ascending: false }).limit(10);
  console.log('fred_treasury_10y top 10:', fredFed?.map(r => `${r.reference_month}: ${r.fred_treasury_10y}`));

  // KOSIS
  let { data: kosis } = await supabase.from('indicator_kosis_monthly_logs').select('cpi_total, reference_date').order('cpi_total', { ascending: false }).limit(10);
  console.log('cpi_total top 10:', kosis?.map(r => `${r.reference_date}: ${r.cpi_total}`));
}

run().catch(console.error);
