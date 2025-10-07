package com.example.fraud.generator;

import com.example.fraud.monitor.PerformanceMonitor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

public class TransactionScheduler {

    private static final Logger logger = LoggerFactory.getLogger(TransactionScheduler.class);
    private static final int SCHEDULER_TPS_CAPACITY = 100;
    private static final double READY_TIMEOUT_SECONDS = 10.0;

    private final TransactionWorker transactionWorker;
    private final PerformanceMonitor performanceMonitor;

    private final List<Thread> schedulerWorkers = new ArrayList<>();
    private final AtomicInteger readyWorkersCount = new AtomicInteger(0);
    private final Lock readyWorkersLock = new ReentrantLock();
    private final ThreadLocal<Map<String, Object>> taskDataCache =
            ThreadLocal.withInitial(HashMap::new);
    private volatile boolean running = false;
    private volatile int targetTps = 0;
    private CountDownLatch workersReadyLatch;
    private CountDownLatch startTimingLatch;

    public TransactionScheduler(TransactionWorker transactionWorker, PerformanceMonitor performanceMonitor) {
        this.transactionWorker = transactionWorker;
        this.performanceMonitor = performanceMonitor;
    }

    public boolean startGeneration(int tps) {
        if (running) {
            return false;
        }
        performanceMonitor.resetMetrics();
        running = true;

        int schedulersNeeded = Math.max(1, tps / SCHEDULER_TPS_CAPACITY);
        int tpsPerWorker = tps / schedulersNeeded;

        workersReadyLatch = new CountDownLatch(1);
        startTimingLatch = new CountDownLatch(1);
        readyWorkersCount.set(0);

        logger.info("Starting {} scheduler workers for {} TPS ({} TPS each)",
                schedulersNeeded, tps, tpsPerWorker);

        for (int i = 0; i < schedulersNeeded; i++) {
            final int schedulerId = i;
            final int totalSchedulers = schedulersNeeded;
            Thread worker = new Thread(
                    () -> generationLoop(tpsPerWorker, schedulerId, totalSchedulers),
                    "scheduler_worker_" + i
            );
            worker.setDaemon(true);
            worker.start();
            schedulerWorkers.add(worker);
        }

        logger.debug("Waiting for all scheduler workers to be ready...");
        try {
            if (workersReadyLatch.await((long) READY_TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
                logger.debug("All scheduler workers ready - starting synchronized timing");

                startTimingLatch.countDown();
                return true;
            } else {
                logger.error("Timeout waiting for scheduler workers to be ready after {}s", READY_TIMEOUT_SECONDS);
                stopGeneration();
                return false;
            }
        } catch (InterruptedException e) {
            logger.error("Interrupted while waiting for workers");
            Thread.currentThread().interrupt();
            stopGeneration();
            return false;
        }
    }

    public boolean stopGeneration() {
        if (!running) {
            return false;
        }

        targetTps = 0;
        running = false;

        if (startTimingLatch != null) {
            startTimingLatch.countDown();
        }

        for (Thread worker : schedulerWorkers) {
            try {
                worker.join(2000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }

        schedulerWorkers.clear();
        readyWorkersCount.set(0);

        logger.debug("Transaction generation stopped");
        return true;
    }

    private void generationLoop(int workerTps, int workerId, int totalWorkers) {
        double interval = 1.0 / workerTps;

        logger.debug("Scheduler worker {} ready", workerId);

        // Signal this worker is ready
        readyWorkersLock.lock();
        try {
            int count = readyWorkersCount.incrementAndGet();
            if (count == totalWorkers) {
                logger.info("All {} scheduler workers ready", totalWorkers);
                workersReadyLatch.countDown();
            }
        } finally {
            readyWorkersLock.unlock();
        }

        logger.debug("Scheduler worker {} waiting for start signal...", workerId);
        try {
            if (!startTimingLatch.await(15, TimeUnit.SECONDS)) {
                logger.error("Scheduler worker {} timeout waiting for start signal", workerId);
                return;
            }
        } catch (InterruptedException e) {
            logger.error("Scheduler worker {} interrupted", workerId);
            Thread.currentThread().interrupt();
            return;
        }

        logger.debug("Scheduler worker {} starting synchronized generation", workerId);
        double nextTime = System.nanoTime() / 1_000_000_000.0;

        long currentSecond = System.currentTimeMillis() / 1000;
        int transactionsThisSecond = 0;
        int maxTransactionsPerSecond = (int) (workerTps * 1.5);

        while (running) {

            double currentTime = System.nanoTime() / 1_000_000_000.0;
            long currentTimeSecond = System.currentTimeMillis() / 1000;

            if (currentTimeSecond != currentSecond) {
                currentSecond = currentTimeSecond;
                transactionsThisSecond = 0;
            }

            if (transactionsThisSecond >= maxTransactionsPerSecond) {
                double sleepUntilNextSecond = (currentSecond + 1) - (System.currentTimeMillis() / 1000.0);
                if (sleepUntilNextSecond > 0) {
                    try {
                        Thread.sleep((long) Math.min(100, sleepUntilNextSecond * 1000));
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
                continue;
            }

            if (currentTime >= nextTime) {
                Map<String, Object> taskData = taskDataCache.get();
                taskData.put("scheduled_time", currentTime);
                taskData.put("amount", 100.0 + Math.random() * 14900.0);
                taskData.put("type", getRandomTransactionType());

                try {
                    transactionWorker.submitTransaction(taskData);
                    performanceMonitor.recordTransactionScheduled();
                    transactionsThisSecond++;

                    if (transactionsThisSecond >= maxTransactionsPerSecond * 0.9) {
                        logger.debug("Scheduler worker approaching rate limit: {}/{} TPS",
                                transactionsThisSecond, maxTransactionsPerSecond);
                    }
                } catch (Exception e) {
                    logger.debug("Transaction submission failed (thread pool full): {}", e.getMessage());
                }

                nextTime += interval;
            } else {
                double sleepTime = Math.min(0.001, nextTime - currentTime);
                try {
                    Thread.sleep((long) (sleepTime * 1000));
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    private String getRandomTransactionType() {
        String[] types = {"transfer", "payment", "deposit", "withdrawal"};
        return types[new Random().nextInt(types.length)];
    }

    public Map<String, Object> getStatus() {
        Map<String, Object> status = new HashMap<>();
        status.put("running", running);
        status.put("target_tps", targetTps);
        status.put("scheduler_workers", schedulerWorkers.size());

        List<String> workerNames = new ArrayList<>();
        for (Thread worker : schedulerWorkers) {
            workerNames.add(worker.getName());
        }
        status.put("worker_names", workerNames);

        return status;
    }

    public void shutdown() {
        running = false;
        transactionWorker.shutdown();
    }
}