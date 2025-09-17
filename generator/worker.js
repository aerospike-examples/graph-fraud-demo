const { parentPort } = require("worker_threads");
const { Agent } = require("undici");
const baseUrl = process.env.BACKEND_URL ?? "http://0.0.0.0:4000";
const agent = new Agent({
  connections: 8,
  pipelining: 3,
  keepAliveTimeout: 10_000,
  keepAliveMaxTimeout: 30_000,
});

async function createTransaction() {
  try{
    const res = await fetch(`${baseUrl}/transaction-generation/generate`, {
      method: "POST",
      dispatcher: agent,
      headers: { "content-type": "application/json" },
      body: "{}",
    });

    if (res.status === 503 || res.status === 429) {
      parentPort.postMessage({ status: 'rate-limit' })
      return
    }

    parentPort.postMessage({ status: 'success' })
  } catch(error) {
      console.error(`Error creating transaction: ${error}`)
      parentPort.postMessage({ status: 'error', error: error.message })
  }
}

let running = false;
let count = 0;
async function runAtRate(rate) {

  while (running) {
    const started = Date.now();
    try {
      await createTransaction();
      parentPort.postMessage({ status: "created" });
    } catch (e) {
      console.error(`Transaction creation failed: ${e.message}`);
      parentPort.postMessage({ status: "error", error: e.message });
    }
    count++;
    if(count % 50 === 0) console.log(`At ${count} requests sent`);

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
