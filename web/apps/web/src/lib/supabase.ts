"use client";

import { createClient } from "@supabase/supabase-js";
import type { SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;
let unavailable: string | null = null;

/** Lazily create the browser Supabase client. Returns null when not configured. */
export function getSupabase(): SupabaseClient | null {
  if (client) return client;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) {
    unavailable = "Supabase is not configured (NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY).";
    return null;
  }
  client = createClient(url, anon, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: false,
    },
  });
  return client;
}

export function supabaseUnavailableReason(): string | null {
  return unavailable;
}

/** Ensure an anonymous session exists so rows are scoped to this browser. */
export async function ensureSession(): Promise<boolean> {
  const sb = getSupabase();
  if (!sb) return false;
  const { data, error } = await sb.auth.getSession();
  if (error) return false;
  if (data.session) return true;
  const { error: signInError } = await sb.auth.signInAnonymously();
  return !signInError;
}