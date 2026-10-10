import { createClient } from "@supabase/supabase-js";
import type { SupabaseClient } from "@supabase/supabase-js";
import { createServer } from "node:http";
import { executeRun } from "./runner.ts";
import type { RunRow } from "./runner.ts";

function env(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function makeSupabase(): SupabaseClient {
  return createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

const POLL_MS = Number(process.env.POLL_INTERVAL_MS ?? "1500");
const LEASE_SECONDS = Number(process.env.LEASE_SECONDS ?? "300");

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main(): Promise<void> {
  const supabase = makeSupabase();

  // Free hosting tiers (Render, Koyeb) spin services down after idle time.
  // Expose a health endpoint so a pinger / platform health check counts as
  // inbound traffic and keeps the poller awake. Harmless elsewhere.
  const port = Number(process.env.PORT ?? "8080");
  createServer((_req, res) => {
    res.writeHead(200, { "content-type": "text/plain" });
    res.end("gform-duga worker ok");
  }).listen(port, () => {
    console.log(`health endpoint listening on :${port}`);
  });

  let running = false;
  let currentRunId: number | null = null;
  let shuttingDown = false;

  const releaseCurrentRun = async (): Promise<void> => {
    if (currentRunId === null) return;
    const { error } = await supabase
      .from("runs")
      .update({ status: "queued", claimed_until: null })
      .eq("id", currentRunId);
    if (error) console.error(`could not release run ${currentRunId}:`, error.message);
    console.log(`released run ${currentRunId} back to the queue`);
  };

  const tryExecute = async (run: RunRow): Promise<void> => {
    running = true;
    currentRunId = run.id;
    console.log(`claimed run ${run.id} (${run.count} submissions)`);
    try {
      await executeRun(supabase, run, LEASE_SECONDS);
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : String(exc);
      console.error(`run ${run.id} crashed:`, message);
      const { error } = await supabase
        .from("runs")
        .update({ status: "failed", error: message.slice(0, 500) })
        .eq("id", run.id);
      if (error) console.error(error.message);
    } finally {
      running = false;
      currentRunId = null;
    }
  };

  const loop = async (): Promise<void> => {
    while (!shuttingDown) {
      if (running) {
        await sleep(POLL_MS);
        continue;
      }

      const { data, error } = await supabase.rpc("claim_next_run", {
        lease_seconds: LEASE_SECONDS,
      });

      if (error) {
        console.error("claim_next_run failed:", error.message);
        await sleep(POLL_MS * 5);
        continue;
      }
      if (!data) {
        await sleep(POLL_MS);
        continue;
      }
      // PostgREST serializes a NULL composite as {} — a truthy but unusable
      // payload. Guard on the returned id so an empty queue means "sleep".
      const run = data as Partial<RunRow>;
      if (typeof run.id !== "number") {
        await sleep(POLL_MS);
        continue;
      }

      if (shuttingDown) {
        await releaseCurrentRun();
        return;
      }
      await tryExecute(run as RunRow);
    }
  };

  process.on("SIGINT", async () => {
    shuttingDown = true;
    await releaseCurrentRun();
    process.exit(0);
  });
  process.on("SIGTERM", async () => {
    shuttingDown = true;
    await releaseCurrentRun();
    process.exit(0);
  });
  process.on("unhandledRejection", (reason) => {
    console.error("unhandled rejection:", reason);
  });

  console.log(
    `gform-duga worker online (poll ${POLL_MS}ms, lease ${LEASE_SECONDS}s)`,
  );
  await loop();
}

main().catch((exc) => {
  console.error("fatal:", exc instanceof Error ? exc.message : exc);
  process.exit(1);
});