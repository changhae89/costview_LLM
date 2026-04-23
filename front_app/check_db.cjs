const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8020').replace(/\/$/, '');

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function run() {
  console.log('--- Backend API DB Check ---');

  const [metrics, monthly] = await Promise.all([
    apiGet('/api/v1/mobile/dashboard-metrics'),
    apiGet('/api/v1/mobile/indicators/monthly'),
  ]);

  const latest = metrics.latest || {};
  console.log('ai_gpr_index:', latest.ai_gpr_index, latest.dates?.ai_gpr_index);
  console.log('krw_usd_rate:', latest.krw_usd_rate, latest.dates?.krw_usd_rate);
  console.log('fred_wti:', latest.fred_wti, latest.dates?.fred_wti);
  console.log('fred_treasury_10y:', latest.fred_treasury_10y, latest.dates?.fred_treasury_10y);
  console.log('cpi_total:', latest.cpi_total, latest.dates?.cpi_total);
  console.log('monthly rows:', monthly.length);
}

run().catch(error => {
  console.error('[check_db] backend api error:', error.message);
  process.exitCode = 1;
});
