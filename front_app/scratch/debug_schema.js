const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8020').replace(/\/$/, '');

async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function checkSchema() {
  const [chains, news, monthly] = await Promise.all([
    apiGet('/api/v1/mobile/causal-chains'),
    apiGet('/api/v1/mobile/news?limit=1'),
    apiGet('/api/v1/mobile/indicators/monthly'),
  ]);

  console.log('--- causal chain sample keys ---');
  console.log(Object.keys(chains[0] || {}));

  console.log('\n--- news sample keys ---');
  console.log(Object.keys(news.data?.[0] || {}));

  console.log('\n--- monthly indicator sample keys ---');
  console.log(Object.keys(monthly[0] || {}));
}

checkSchema().catch(error => {
  console.error('[debug_schema] backend api error:', error.message);
  process.exitCode = 1;
});
