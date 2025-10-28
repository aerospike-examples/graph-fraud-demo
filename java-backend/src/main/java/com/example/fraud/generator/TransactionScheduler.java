package com.example.fraud.generator;

import com.example.fraud.model.TransactionType;
import com.example.fraud.monitor.PerformanceMonitor;
import com.example.fraud.util.FraudUtil;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ThreadLocalRandom;
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
    private volatile boolean running = false;
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
        performanceMonitor.resetPerformanceSummary();
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
        if (workerTps <= 0.0) {
            throw new IllegalArgumentException("workerTps must be > 0");
        }
        final long nanosPerTxn = Math.max(1L, (long) Math.floor(1_000_000_000.0 / workerTps));
        final Duration interval = Duration.ofNanos(nanosPerTxn);

        logger.debug("Scheduler worker {} ready (interval ~{}μs for {} TPS)",
                workerId, nanosPerTxn / 1_000, workerTps);

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

        Instant nextTime = Instant.now();
        long currentSecond = nextTime.getEpochSecond();
        int transactionsThisSecond = 0;

        final int maxTransactionsPerSecond =
                (int) Math.max(1, Math.ceil(workerTps * 1.5));

        while (running) {
            final Instant now = Instant.now();

            final long epochSecond = now.getEpochSecond();
            if (epochSecond != currentSecond) {
                currentSecond = epochSecond;
                transactionsThisSecond = 0;
            }

            if (transactionsThisSecond >= maxTransactionsPerSecond) {
                final Instant nextSecond = Instant.ofEpochSecond(currentSecond + 1);
                Duration untilNext = Duration.between(now, nextSecond);
                if (!untilNext.isNegative() && !untilNext.isZero()) {
                    try {
                        Thread.sleep(Math.min(100, untilNext.toMillis()));
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
                continue;
            }

            if (!now.isBefore(nextTime)) {
                Instant scheduledTime = now;
                double amount = 100.0 + ThreadLocalRandom.current().nextDouble(14900.0);
                TransactionType type = FraudUtil.getRandomTransactionType();
                TransactionTask task = new TransactionTask(scheduledTime, amount, type);

                try {
                    transactionWorker.submitTransaction(task);
                    transactionsThisSecond++;

                    if (transactionsThisSecond >= (int) (maxTransactionsPerSecond * 0.9)) {
                        logger.debug("Scheduler worker approaching rate limit: {}/{} TPS",
                                transactionsThisSecond, maxTransactionsPerSecond);
                    }
                } catch (Exception e) {
                    logger.debug("Transaction submission failed (thread pool full): {}", e.getMessage());
                }

                nextTime = nextTime.plus(interval);
            } else {
                Duration sleep = Duration.between(now, nextTime);
                if (sleep.compareTo(Duration.ofMillis(1)) > 0) {
                    sleep = Duration.ofMillis(1);
                }
                long millis = Math.max(0L, sleep.toMillis());
                if (millis > 0) {
                    try {
                        Thread.sleep(millis);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
    }

    public void shutdown() {
        running = false;
        transactionWorker.shutdown();
    }
}