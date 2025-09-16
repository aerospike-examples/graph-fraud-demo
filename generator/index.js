const express = require("express");
const cors = require("cors");
const http = require("http");
const { Worker } = require("worker_threads");

const app = express();
app.use(express.json());
app.use(cors({origin: "*"}));
const server = http.createServer(app);

const workers = []
const baseUrl = process.env.BACKEND_URL ?? "http://localhost:4000"

let maxRate = 200
let currentRate = 0
let running = false
let total = 0
let errors = 0
let startTime = null

const startWorkers = async (rate, start) => {
  startTime = start;
  running = true;
  total = 0;
  errors = 0;
  currentRate = rate;

  // Limit workers to prevent overwhelming backend - more conservative
  const maxWorkersPerRate = Math.min(Math.ceil(rate / 3), 3); // Max 3 workers, 25 TPS each
  const ratePerWorker = Math.ceil(rate / maxWorkersPerRate);

  console.log(
    `Starting ${maxWorkersPerRate} workers at ${ratePerWorker} TPS each for total ${rate} TPS`
  );

  for (let i = 0; i < maxWorkersPerRate; i++) {
    workers.push(new Worker("./worker.js"));
    workers[i]?.on("message", listenToWorker);

    if (i > 0) {
      await new Promise((resolve) => setTimeout(resolve, 50 * i)); // 50ms delay between workers
    }

    // Calculate rate for this worker
    const workerRate =
      i === maxWorkersPerRate - 1
        ? rate - ratePerWorker * (maxWorkersPerRate - 1) // Last worker gets remainder
        : ratePerWorker;

    console.log(`Starting worker ${i + 1} with rate ${workerRate} TPS`);
    workers[i].postMessage({ start: true, rate: workerRate });
  }
};

const stopWorkers = async () => {
  try {
    while (workers?.length > 0) {
      workers[0]?.terminate();
      workers.shift();
    }
    running = false;
    total = 0;
    errors = 0;
    return;
  } catch (e) {
    console.error(`Error stopping workers: {e}`);
    return;
  }
};

const listenToWorker = async (data) => {
  const { status, error } = data;
  if (status === "created") {
    total++;
  }
  if (status === "error") {
    errors++;
    if (error) {
      console.error(`Worker error: ${error}`);
    }

    // Stop if too many errors (reduced threshold)
    if (errors > 50) {
      console.error(`Too many errors (${errors}), stopping workers`);
      await stopWorkers();
    }
  }
};

app.post("/generate/start", async (req, res) => {
  if (running) {
    res.send({ error: "Generation already running" });
    return;
  }

  const { rate, start } = req.body;
  if (rate > maxRate) {
    res.send({ error: "Rate is greater than maximum rate" });
    return;
  }

  try {
    const response = await fetch(`${baseUrl}/performance/reset`, {
      method: "POST",
    });
    if (response.ok) {
      await startWorkers(rate, start);
      res.send({ status: "running" });
      return;
    } else {
      throw new Error(
        `Error reseting performance monitor: ${response.statusText}`
      );
    }
  } catch (e) {
    console.error(e.message);
    res.send({ error: e.message });
  }
});

app.post("/generate/stop", async (_, res) => {
    if(!running) {
        res.send({ error: "Generation not running" })
        return
    }
    stopWorkers()
    .then(() => {
        res.send({ status: "stopped" })
    })
    .catch(error => res.send({ error }))
})

app.get("/generate/status", async (_, res) => {
    res.send({
        running,
        total,
        startTime,
        currentRate,
        maxRate,
        errors
    })
})
