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
let rateLimit = 0
let startTime = null

const startWorkers = async (rate, start) => {
  startTime = start;
  running = true;
  total = 0;
  errors = 0;
  currentRate = rate;

  const numWorkers = Math.ceil(rate / 100)
  const remainder = rate % 100

  console.log(
      `Starting ${numWorkers} workers for total ${rate} TPS`
  );

  for(let i = 0; i < numWorkers; i++) {
    workers.push(new Worker('./worker.js'))
    workers[i]?.on("message", listenToWorker)
    if(remainder && i === numWorkers - 1) {
      workers[i].postMessage({ start: true, rate: remainder })
    }
    else workers[i].postMessage({ start: true, rate: 100 })
  }
};

const stopWorkers = async () => {
  try {
    while (workers?.length > 0) {
      workers[0]?.terminate();
      workers.shift();
    }
    running = false;
  } catch (e) {
    console.error(`Error stopping workers: {e}`);
  }
};

const listenToWorker = async (data) => {
  const { status, error } = data;
  if (status === "created") {
    total++;
  }else if (status === "rate-limit"){
    rateLimit++;
  }else if (status === "error"){
    errors++;
    console.log(`ERROR: ${error}`)
  }
  if ((total + errors) % 50 === 0) {
    console.log(`Success: ${total}, Rate Limit: ${rateLimit}, Errors: ${errors}`);
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
      total_attempts = 0;
      total_success = 0;
      total_rate_limited = 0;
      total_rejected = 0;
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

server.listen(4001, () => {
  console.log("Generator listening on port 4001");
  console.log(`Backend URL: ${baseUrl}`);
});