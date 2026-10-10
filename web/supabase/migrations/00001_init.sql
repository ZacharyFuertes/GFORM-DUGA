-- GFORM-DUGA: forms / presets / runs / run_events + RLS + worker RPCs + realtime.
-- Clients (anonymous auth) create and read their own rows. The Railway worker
-- uses the service-role key: it bypasses RLS, calls claim_next_run(),
-- inserts run_events, and updates runs directly.

-- ============================ TABLES ============================

create table if not exists public."forms" (
  id          bigint generated always as identity primary key,
  user_id     uuid not null default auth.uid(),
  url         text not null,
  title       text not null default '',
  description text not null default '',
  schema      jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  constraint forms_user_url_unique unique (user_id, url)
);

create table if not exists public."presets" (
  id         bigint generated always as identity primary key,
  user_id    uuid not null default auth.uid(),
  form_id    bigint references public.forms(id) on delete cascade,
  name       text not null default '',
  config     jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public."runs" (
  id           bigint generated always as identity primary key,
  user_id      uuid not null default auth.uid(),
  form_id      bigint references public.forms(id) on delete cascade,
  url          text not null,
  config       jsonb not null default '{}'::jsonb,
  count        integer not null default 1 check (count >= 1 and count <= 100),
  status       text not null default 'queued'
               check (status in ('queued','running','done','failed','cancelled')),
  progress     integer not null default 0,
  error        text,
  claimed_until timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists runs_status_created_idx on public.runs (status, created_at);
create index if not exists runs_user_created_idx on public.runs (user_id, created_at);

create table if not exists public."run_events" (
  id         bigint generated always as identity primary key,
  run_id     bigint not null references public.runs(id) on delete cascade,
  seq        integer not null,
  level      text not null default 'info' check (level in ('info','ok','warn','err')),
  message    text not null default '',
  data       jsonb,
  created_at timestamptz not null default now()
);

create index if not exists run_events_run_seq_idx on public.run_events (run_id, seq);

-- ============================ UPDATED_AT ============================

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists runs_touch on public.runs;
create trigger runs_touch
  before update on public.runs
  for each row execute function public.touch_updated_at();

-- ============================ RLS ============================

alter table public.forms     enable row level security;
alter table public.presets   enable row level security;
alter table public.runs      enable row level security;
alter table public.run_events enable row level security;

do $$
declare
  table_name text;
begin
  foreach table_name in array array['forms', 'presets', 'runs']
  loop
    execute format('
      drop policy if exists %I on public.%I;
      create policy %I on public.%I
        for select using (auth.uid() = user_id);
      create policy %I on public.%I
        for insert with check (auth.uid() = user_id);
      create policy %I on public.%I
        for update using (auth.uid() = user_id);
      create policy %I on public.%I
        for delete using (auth.uid() = user_id);',
      table_name || '_select_own', table_name,
      table_name || '_select_own', table_name,
      table_name || '_insert_own', table_name,
      table_name || '_update_own', table_name,
      table_name || '_delete_own', table_name);
  end loop;
end;
$$;

-- run_events has no user_id column: scope reads through the owning run.
drop policy if exists run_events_select_own on public.run_events;
create policy run_events_select_own on public.run_events
  for select using (
    auth.uid() = (select user_id from public.runs where id = run_id)
  );

-- Clients never insert/update/delete rows in run_events or claim runs:
-- only the service-role worker does.

-- ============================ WORKER RPCs ============================

-- Claim the oldest queueable run, or reclaim one whose lease expired.
-- security definer + explicit grants keep this out of the hands of
-- anon/authenticated clients. Mirrors "FOR UPDATE SKIP LOCKED" semantics.
create or replace function public.claim_next_run(lease_seconds int default 300)
returns public.runs
language plpgsql
security definer
set search_path = public
as $$
declare
  v_run public.runs;
begin
  select * into v_run
  from public.runs
  where status = 'queued'
     or (status = 'running' and claimed_until is not null and claimed_until < now())
  order by created_at asc
  limit 1
  for update skip locked;

  if v_run is null then
    return null;
  end if;

  update public.runs
     set status = 'running',
         claimed_until = now() + make_interval(secs => lease_seconds),
         updated_at = now()
   where id = v_run.id
   returning * into v_run;

  return v_run;
end;
$$;

-- Refresh the lease so a long run is not reclaimed mid-flight.
create or replace function public.heartbeat_run(target bigint, lease_seconds int default 300)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.runs
     set claimed_until = now() + make_interval(secs => lease_seconds),
         updated_at = now()
   where id = target and status = 'running';
end;
$$;

revoke execute on function public.claim_next_run(int) from public, anon, authenticated;
revoke execute on function public.heartbeat_run(bigint, int) from public, anon, authenticated;
grant execute on function public.claim_next_run(int) to service_role;
grant execute on function public.heartbeat_run(bigint, int) to service_role;

-- ============================ REALTIME ============================

do $$
begin
  begin
    alter publication supabase_realtime add table public.runs;
  exception when duplicate_object then null;
  end;
  begin
    alter publication supabase_realtime add table public.run_events;
  exception when duplicate_object then null;
  end;
end;
$$;