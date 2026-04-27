import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.SUPABASE_URL as string
const SUPABASE_KEY = import.meta.env.SUPABASE_KEY as string

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)
