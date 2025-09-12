const { parentPort } = require("worker_threads");
const { Agent, setGlobalDispatcher} = require("undici");
const baseUrl = process.env.BACKEND_URL ?? "http://localhost:4000";

const agent = new Agent({
  connections: 64,
  pipelining: 1,
  keepAliveTimeout: 10_000,
  keepAliveMaxTimeout: 30_000,
});
setGlobalDispatcher(agent);

async function createTransaction() {
  const res = await fetch(`${baseUrl}/transaction-generation/generate`, {
    method: "POST",
    dispatcher: agent,
    headers: { "content-type": "application/json" },
    body: "{}"
  });

  if (res.body) await res.text();
}

let running = false;
async function runAtRate(rate) {
  const period = 1000 / rate;
  while (running) {
    const started = Date.now();
    try {
      await createTransaction();
      parentPort.postMessage({ status: "created" });
    } catch (e) {
      console.error(e);
      parentPort.postMessage({ status: "error" });
    }
    const elapsed = Date.now() - started;
    const sleep = Math.max(0, period - elapsed);
    if (sleep) await new Promise(r => setTimeout(r, sleep));
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
