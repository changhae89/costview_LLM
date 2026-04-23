const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8020').replace(/\/$/, '');

async function test() {
  console.log('Testing backend API connection...');
  const response = await fetch(`${API_BASE_URL}/api/v1/mobile/news?limit=1`);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  const data = await response.json();
  console.log('Success! Data fetched:', data.data?.length ?? 0);
}

test().catch(error => {
  console.error('Backend API test failed:', error.message);
  process.exitCode = 1;
});
