const { parentPort } = require('worker_threads');
const baseUrl = process.env.BACKEND_URL ?? "http://localhost:4000"
const http = require('http');


const httpAgent = new http.Agent({
    keepAlive: true,
    maxSockets: 5,
    maxFreeSockets: 2,
    timeout: 5000,
    freeSocketTimeout: 30000
});

const createTransaction = async () => {
    try {
        await fetch(`${baseUrl}/transaction-generation/generate`, {
            method: "POST",
            agent: httpAgent
        })
        parentPort.postMessage({ status: "created" })
    }
    catch(error) {
        console.error(`Error creating transaction: ${error}`)
        parentPort.postMessage({ status: 'error' })
    }
}

parentPort.on("message", (data) => {
    const { start, stop, rate } = data;
    let task = null
    if(start) {
        task = setInterval(async () => await createTransaction(), (1000/rate))
        parentPort.postMessage({ status: "running" });
    }
    if(stop) {
        if(task) clearInterval(task)
        parentPort.postMessage({ status: "stopped" });
    }
})
