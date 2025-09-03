const express = require("express");
const cors = require("cors");
const http = require("http");
const { Worker } = require("worker_threads");

const app = express();
app.use(express.json());
app.use(cors({origin: "*"}));
const server = http.createServer(app);

const baseUrl = process.env.BACKEND_URL ?? "http://localhost:4000"
const workers = []
let running = false

app.post("/generate/start", async (req, res) => {
    if(running) return res.send({ status: "Generation already running" })
    const { rate } = req.body
    const startTime = new Date().toISOString()
    const response = await fetch(`${baseUrl}/transaction-generation/start?rate=${rate}&start=${startTime}`, {
		method: 'POST'
    })
    if(response.ok) {
        running = true
        const numWorkers = Math.ceil(rate / 100)
        const remainder = rate % 100
        
        for(let i = 0; i < numWorkers; i++) {
            workers.push(new Worker('./worker.js'))
            if(remainder && i === numWorkers - 1) {
                workers[i].postMessage({ start: true, rate: remainder })
            }
            else workers[i].postMessage({ start: true, rate: 100 })
        }
        res.send({ status: "running" })
    }
    else res.send({ error: "Could not start generator" })
})

app.get("/generate/stop", async (req, res) => {
    if(!running) res.send({ status: "Generation not running" })
    while(workers.length > 0) {
        workers[0]?.terminate();
        workers.shift();
    }
    const response = await fetch(`${baseUrl}/transaction-generation/stop`, { method: "POST" })
    if(response.ok) {
        running = false
        res.send({ status: "stopped" })
        return
    }
})

server.listen(4001, () => console.log("Listening on port 4001"))