package com.example.fraud.generator;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.fraud.TransactionInfo;

import java.util.concurrent.atomic.AtomicInteger;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


import java.util.concurrent.*;

public class TransactionWorker {
    private final GeneratorService generatorService;
    private final FraudService fraudService;
    private static final Logger logger = LoggerFactory.getLogger(TransactionWorker.class);

    private final int WORKER_POOL_SIZE;

    private final AtomicInteger successfulTransactions;

    private volatile boolean running = false;
    private ExecutorService executor;

    public TransactionWorker(GeneratorService generatorService, FraudService fraudService,
                             int workerPoolSize) {
        this.generatorService = generatorService;
        this.fraudService = fraudService;
        WORKER_POOL_SIZE = workerPoolSize;

        successfulTransactions = new AtomicInteger(0);
    }

    public void startWorkers() {
        running = true;
        executor = Executors.newFixedThreadPool(WORKER_POOL_SIZE, new ThreadFactory() {
            private int counter = 0;

            @Override
            public Thread newThread(Runnable r) {
                Thread t = new Thread(r);
                t.setName("txn_fraud_worker-" + counter++);
                return t;
            }
        });

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

    public void submitTransaction(TransactionTask taskData) {
        if (!running) {
            throw new RuntimeException("Workers not started");
        }
        executor.submit(() -> executeTransaction(taskData));
    }


    private void executeTransaction(TransactionTask taskData) {
        try {
            TransactionInfo result = generatorService.generateTransaction(taskData);

            if (result != null &&
                    result.success() &&
                    result.edgeId() != null &&
                    result.txnId() != null) {
                successfulTransactions.incrementAndGet();
                fraudService.submitFraudDetection(result);
            } else {
                logger.warn("Transaction creation failed");
            }

        } catch (Exception e) {
            logger.error("Transaction+Fraud execution error: {}", e.toString());
        }
    }

    public int getSuccessfulTransactions() {
        return successfulTransactions.get();
    }

    public void clearSuccessfulTransactions() {
        successfulTransactions.set(0);
    }
}