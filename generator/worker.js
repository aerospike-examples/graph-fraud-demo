const { parentPort } = require('worker_threads');
const baseUrl = process.env.BACKEND_URL ?? "http://localhost:4000"

const createTransaction = async () => {
    try {
        const res = await fetch(`${baseUrl}/transaction-generation/generate`, {
            method: "POST"
        })
        if(!res.ok) return false
        return true
    }
    catch(e) {
        console.error(`Error creating transaction: ${e}`)
    }
}

parentPort.on("message", (data) => {
    const { start, stop, rate } = data;
    let task = null
    if(start) {
        task = setInterval(async () => await createTransaction(), (1000/rate))
        parentPort.postMessage("Started");
    }
    if(stop) {
        if(task) clearInterval(task)
        parentPort.postMessage("Stopped");
    }
})
