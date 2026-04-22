
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.local' });

const supabase = createClient(
  process.env.EXPO_PUBLIC_SUPABASE_URL || '',
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || ''
);

async function checkSchema() {
  console.log('--- causal_chains sample ---');
  const { data: cData, error: cError } = await supabase.from('causal_chains').select('*').limit(1);
  if (cError) console.error('causal_chains error:', cError);
  else console.log('causal_chains columns:', Object.keys(cData[0] || {}));

  console.log('\n--- news_analyses sample ---');
  const { data: nData, error: nError } = await supabase.from('news_analyses').select('*').limit(1);
  if (nError) console.error('news_analyses error:', nError);
  else console.log('news_analyses columns:', Object.keys(nData[0] || {}));

  console.log('\n--- raw_news sample ---');
  const { data: rData, error: rError } = await supabase.from('raw_news').select('*').limit(1);
  if (rError) console.error('raw_news error:', rError);
  else console.log('raw_news columns:', Object.keys(rData[0] || {}));
}

checkSchema();
