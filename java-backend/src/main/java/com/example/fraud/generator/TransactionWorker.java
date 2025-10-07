package com.example.fraud.generator;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.monitor.PerformanceMonitor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.*;

public class TransactionWorker {

    private static final Logger logger = LoggerFactory.getLogger(TransactionWorker.class);
    private final int WORKER_POOL_SIZE;
    private final int WORKER_MAX_POOL_SIZE;

    private final GeneratorService generatorService;
    private final FraudService fraudService;
    private final PerformanceMonitor performanceMonitor;

    private volatile boolean running = false;
    private ExecutorService executor;

    public TransactionWorker(GeneratorService generatorService, FraudService fraudService,
                             PerformanceMonitor performanceMonitor, int workerPoolSize, int workerMaxPoolSize) {
        this.generatorService = generatorService;
        this.fraudService = fraudService;
        this.performanceMonitor = performanceMonitor;
        WORKER_POOL_SIZE = workerPoolSize;
        WORKER_MAX_POOL_SIZE = workerMaxPoolSize;
    }

    public void startWorkers() {
        running = true;
        executor = new ThreadPoolExecutor(
                WORKER_POOL_SIZE,
                WORKER_MAX_POOL_SIZE,
                60L,
                TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(),
                new ThreadFactory() {
                    private int counter = 0;

                    @Override
                    public Thread newThread(Runnable r) {
                        Thread t = new Thread(r);
                        t.setName("txn_fraud_worker-" + counter++);
                        return t;
                    }
                }
        );

        logger.debug("Transaction workers ready ({} workers)", WORKER_POOL_SIZE);
    }

    public void stopWorkers() {
        running = false;
        shutdown();
        logger.debug("Transaction workers stopped ({} workers)", WORKER_POOL_SIZE);
    }

    public void shutdown() {
        running = false;
        if (executor != null) {
            try {
                executor.shutdownNow();
                if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                    logger.warn("Executor did not terminate in time");
                }
                logger.debug("Transaction workers stopped");
            } catch (InterruptedException e) {
                logger.warn("Error shutting down worker executor: {}", e.getMessage());
                executor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }
    }

    public Future<?> submitTransaction(Map<String, Object> taskData) {
        if (!running) {
            throw new RuntimeException("Workers not started");
        }
        return executor.submit(() -> executeTransaction(taskData));
    }

    private void executeTransaction(Map<String, Object> taskData) {
        double scheduledTime = (double) taskData.get("scheduled_time");
        long startTime = System.nanoTime();

        double queueWaitMs = (System.nanoTime() / 1_000_000.0) - (scheduledTime * 1000);

        try {
            long dbStartTime = System.nanoTime();
            Map<String, Object> result = generatorService.generateTransaction();
            long dbEndTime = System.nanoTime();
            double dbLatencyMs = (dbEndTime - dbStartTime) / 1_000_000.0;

            if (result != null &&
                    Boolean.TRUE.equals(result.get("success")) &&
                    result.containsKey("edge_id") &&
                    result.containsKey("txn_id")) {

                long endTime = System.nanoTime();
                double totalLatencyMs = (endTime / 1_000_000.0) - (scheduledTime * 1000);
                double executionLatencyMs = (endTime - startTime) / 1_000_000.0;

                performanceMonitor.recordTransactionCompletedDetailed(
                        totalLatencyMs,
                        executionLatencyMs,
                        queueWaitMs,
                        dbLatencyMs
                );

                fraudService.submitFraudDetectionAsync(
                        (String) result.get("edge_id"),
                        (String) result.get("txn_id")
                );

                if (totalLatencyMs > 1000) {
                    logger.info("HIGH LATENCY Transaction {}: Total={}ms (Queue={}ms, DB={}ms)",
                            result.get("txn_id"),
                            Math.round(totalLatencyMs * 10) / 10.0,
                            Math.round(queueWaitMs * 10) / 10.0,
                            Math.round(dbLatencyMs * 10) / 10.0);
                } else if (queueWaitMs > 500) {
                    logger.info("HIGH QUEUE WAIT Transaction {}: Queue={}ms, Total={}ms",
                            result.get("txn_id"),
                            String.format("%.1f", queueWaitMs),
                            String.format("%.1f", totalLatencyMs));
                }
            } else {
                performanceMonitor.recordTransactionFailed();
                logger.warn("Transaction creation failed");
            }

        } catch (Exception e) {
            performanceMonitor.recordTransactionFailed();
            logger.error("Transaction+Fraud execution error: {}", e.getMessage());
        }
    }


    public Map<String, Object> getPoolStatus() {
        Map<String, Object> status = new HashMap<>();

        if (executor == null) {
            status.put("pool_size", 0);
            status.put("running", running);
            status.put("active_threads", 0);
            status.put("queue_size", 0);
            return status;
        }

        ThreadPoolExecutor tpe = (ThreadPoolExecutor) executor;
        status.put("pool_size", tpe.getMaximumPoolSize());
        status.put("running", running);
        status.put("active_threads", tpe.getActiveCount());
        status.put("queue_size", tpe.getQueue().size());

        return status;
    }
}