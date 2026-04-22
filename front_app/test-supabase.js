import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://ijhgmemuzeujpvdlywjn.supabase.co';
const supabaseKey = 'sb_publishable_LXB0xwW4xx_r1K1S8oMLyw_-uu5ydYu';
const supabase = createClient(supabaseUrl, supabaseKey);

async function test() {
  console.log("Testing Supabase connection...");
  const { data, error } = await supabase.from('indicator_daily_logs').select('*').limit(1);
  if (error) {
    console.error("Error connecting to table:", error.message);
  } else {
    console.log("Success! Data fetched:", data);
  }
}

test();
