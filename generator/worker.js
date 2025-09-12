const {parentPort} = require("worker_threads");
const baseUrl = process.env.BACKEND_URL ?? "http://localhost:4000";
const http = require("http");

const httpAgent = new http.Agent({
    keepAlive: true,
    maxSockets: 10,
    maxFreeSockets: 5,
    timeout: 5000,
    freeSocketTimeout: 30000,
});

let activeRequests = 0;
const MAX_CONCURRENT_REQUESTS = 5;

const createTransaction = async () => {
    if (activeRequests >= MAX_CONCURRENT_REQUESTS) {
        return;
    }
    activeRequests++;
    try {
        const response = await fetch(`${baseUrl}/transaction-generation/generate`, {
            method: "POST",
            agent: httpAgent,
        });
        await response.text()
        parentPort.postMessage({status: "created"});
    } catch (error) {
        console.error(`Error creating transaction: ${error}`);
        parentPort.postMessage({status: "error"});
    } finally {
        activeRequests--;
    }
};

parentPort.on("message", (data) => {
    const {start, stop, rate} = data;
    let task = null;
    if (start) {
        const interval = Math.max(1, Math.floor(1000 / (rate / MAX_CONCURRENT_REQUESTS)));
        task = setInterval(async () => {
            // Fire multiple requests per interval for higher TPS
            const requestsPerInterval = Math.min(MAX_CONCURRENT_REQUESTS, Math.ceil(rate / 100));

            for (let i = 0; i < requestsPerInterval; i++) {
                createTransaction(); // Don't await - let them run concurrently
            }
        }, interval);

        parentPort.postMessage({status: "running"});
    }
    if (stop) {
        if (task) clearInterval(task);
        parentPort.postMessage({status: "stopped"});
    }
});

const cleanup = () => {
    httpAgent.destroy();
    process.exit(0);
};

process.on('SIGTERM', cleanup);
process.on('SIGINT', cleanup);
process.on('exit', cleanup);