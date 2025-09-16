const { parentPort } = require("worker_threads");
const { Agent } = require("undici");
const baseUrl = process.env.BACKEND_URL ?? "http://localhost:4000";

const agent = new Agent({
  connections: 4,
  pipelining: 1,
  keepAliveTimeout: 10_000,
  keepAliveMaxTimeout: 30_000,
});

async function createTransaction() {
  const maxRetries = 3;
  let attempt = 0;

  while (attempt < maxRetries) {
    try {
      const res = await fetch(`${baseUrl}/transaction-generation/generate`, {
        method: "POST",
        dispatcher: agent,
        headers: { "content-type": "application/json" },
        body: "{}",
      });

      if (res.status === 503 || res.status === 429) {
        // Service unavailable or too many requests - wait and retry
        attempt++;
        if (attempt < maxRetries) {
          const backoffMs = Math.min(1000 * Math.pow(2, attempt), 5000);
          console.log(
            `${res.status} error, retrying in ${backoffMs}ms (attempt ${attempt}/${maxRetries})`
          );
          await new Promise((r) => setTimeout(r, backoffMs));
          continue;
        }
        throw new Error(`Service unavailable after ${maxRetries} attempts`);
      }

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      if (res.body) await res.text();
      return;
    } catch (error) {
      attempt++;
      if (attempt >= maxRetries) {
        throw error;
      }

      // Wait before retry for other errors
      const backoffMs = Math.min(500 * attempt, 2000);
      console.log(
        `Request failed, retrying in ${backoffMs}ms (attempt ${attempt}/${maxRetries}): ${error.message}`
      );
      await new Promise((r) => setTimeout(r, backoffMs));
    }
  }
}

let running = false;
async function runAtRate(rate) {
  const period = 1000 / rate;
  const jitterRange = period * 0.2; // Increase jitter to 20% to spread requests more
  const minDelay = period * 0.5; // Minimum delay between requests

  while (running) {
    const started = Date.now();
    try {
      await createTransaction();
      parentPort.postMessage({ status: "created" });
    } catch (e) {
      console.error(`Transaction creation failed: ${e.message}`);
      parentPort.postMessage({ status: "error", error: e.message });
    }

    const elapsed = Date.now() - started;
    const jitter = (Math.random() - 0.5) * jitterRange; // Random jitter ±10%
    const sleep = Math.max(minDelay, period - elapsed + jitter); // Ensure minimum delay

    if (sleep > 0) {
      await new Promise((r) => setTimeout(r, sleep));
    }
  }
}

parentPort.on("message", ({ start, stop, rate }) => {
  if (start && !running) {
    running = true;
    runAtRate(rate);
    parentPort.postMessage({ status: "running" });
  }
  if (stop && running) {
    running = false;
    parentPort.postMessage({ status: "stopped" });
  }
});
