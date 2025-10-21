package com.example.fraud.generator;

import com.example.fraud.config.TransactionGenerationProperties;
import com.example.fraud.fraud.FraudService;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.graph.GraphService;
import com.example.fraud.monitor.PerformanceMonitor;
import com.example.fraud.util.FraudUtil;
import java.time.Instant;
import java.util.concurrent.ThreadLocalRandom;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import org.springframework.stereotype.Service;

@Service
public class GeneratorService {

    private static final Logger logger = LoggerFactory.getLogger(GeneratorService.class);
    private static final Logger statsLogger = LoggerFactory.getLogger("fraud_detection.stats");

    private final GraphService graphService;
    private final FraudService fraudService;
    private final PerformanceMonitor performanceMonitor;
    private final TransactionGenerationProperties props;

    private volatile boolean isRunning = false;
    private List<Object> accountVertices = new ArrayList<>();
    private final TransactionWorker transactionWorker;
    private final TransactionScheduler transactionScheduler;

    public GeneratorService(GraphService graphService,
                            FraudService fraudService,
                            PerformanceMonitor performanceMonitor,
                            TransactionGenerationProperties transactionGenerationProperties) {
        this.props = transactionGenerationProperties;
        this.graphService = graphService;
        this.fraudService = fraudService;
        this.performanceMonitor = performanceMonitor;

        this.transactionWorker = new TransactionWorker(this, fraudService,
                props.getTransactionWorkerPoolSize(), props.getTransactionWorkerMaxPoolSize());
        this.transactionScheduler = new TransactionScheduler(transactionWorker, performanceMonitor);
    }

    public void initializeWorkers() {
        logger.debug("Initializing transaction workers...");

        if (accountVertices.isEmpty()) {
            cacheAccountIds();
        }

        transactionWorker.startWorkers();

        logger.debug("Workers initialized and ready");
    }

    public void cacheAccountIds() {
        try {
            logger.debug("Caching account IDs from database...");
            long startTime = System.nanoTime();
            GraphTraversalSource g = graphService.getMainClient();
            if (g == null) {
                logger.error("Graph client not available");
                return;
            }

            List<Object> accountIds = graphService.getAccountIds();

            double cacheTimeMs = (System.nanoTime() - startTime) / 1_000_000.0;
            int accountCount = accountIds.size();

            if (accountCount < 1) {
                logger.warn("No accounts found in database - transaction generation will fail");
            } else {
                logger.info("Cached {} account IDs in {}ms",
                        String.format("%,d", accountCount),
                        String.format("%.1f", cacheTimeMs));
            }

            accountVertices = accountIds;

        } catch (Exception e) {
            logger.error("Error caching account IDs: {}", e.getMessage());
        }
    }

    public int getMaxTransactionRate() {
        return props.getMaxTransactionRate();
    }

    public boolean startGeneration(int rate) {
        if (isRunning) {
            logger.warn("Transaction generation is already running");
            return false;
        }

        initializeWorkers();

        if (accountVertices.isEmpty()) {
            logger.error("No accounts available for transaction generation - ensure database is seeded");
            return false;
        }

        logger.debug("Using {} cached accounts for transaction generation", String.format("%,d", accountVertices.size()));

        try {
            performanceMonitor.resetPerformanceSummary();
            transactionWorker.clearSuccessfulTransactions();

            isRunning = true;

            boolean success = transactionScheduler.startGeneration(rate);
            logger.info("Starting up generator at {} transactions/second", rate);
            performanceMonitor.setGenerationState(true, rate, Instant.now());

            if (!success) {
                performanceMonitor.setGenerationState(false, 0, null);
                isRunning = false;
                return false;
            }

            return true;

        } catch (Exception e) {
            logger.error("Error starting transaction generation: {}", e.getMessage());
            isRunning = false;
            performanceMonitor.setGenerationState(false, 0, null);
            return false;
        }
    }

    public boolean stopGeneration() {
        if (!isRunning) {
            logger.warn("Transaction generation is not running");
            return false;
        }

        isRunning = false;

        if (transactionScheduler != null) {
            transactionScheduler.stopGeneration();
        }
        if (transactionWorker != null) {
            transactionWorker.stopWorkers();
        }
        performanceMonitor.setGenerationState(false, 0, null);

        logger.info("Transaction generation stopped");
        statsLogger.info("STOP: Generation stopped.");
        return true;
    }

    public TransactionInfo generateTransaction() {
        return generateTransaction(new TransactionTask(Instant.now(),
        100.0 + ThreadLocalRandom.current().nextDouble(14900.0),
        FraudUtil.getRandomTransactionType()));
    }

    public TransactionInfo generateTransaction(TransactionTask transactionTask) {
        Instant start = Instant.now();
        try {
            if (accountVertices.size() < 2) {
                logger.error("Insufficient cached accounts for transaction generation");
                throw new RuntimeException("Need at least 2 accounts for transaction generation");
            }
            Random rand = ThreadLocalRandom.current();
            int size = accountVertices.size();
            int idx1 = rand.nextInt(size);
            int idx2 = rand.nextInt(size - 1);
            if (idx2 >= idx1) idx2++;
            Object senderAccountId = accountVertices.get(idx1);
            Object receiverAccountId = accountVertices.get(idx2);

            String location = FraudUtil.getRandomLocation();

            return graphService.createTransaction(
                    senderAccountId.toString(),
                    receiverAccountId.toString(),
                    transactionTask.amount(),
                    transactionTask.transactionType(),
                    "AUTO",
                    location,
                    start
            );

        } catch (Exception e) {
            logger.error("Error generating normal transaction: {}", e.getMessage());
            throw new RuntimeException(e);
        }
    }

    public int getAccountCacheSize() {
        return accountVertices.size();
    }
    public int getSuccessfulTransactions() { return transactionWorker.getSuccessfulTransactions(); }
    public GeneratorStatus getStatus() {
        return performanceMonitor.getGeneratorStatus();
    }
    public void shutdown() {
        try {
            if (isRunning) {
                stopGeneration();
            }

            if (transactionWorker != null) {
                transactionWorker.shutdown();
            }

            if (transactionScheduler != null) {
                transactionScheduler.shutdown();
            }

            logger.info("GeneratorService shutdown complete");
        } catch (Exception e) {
            logger.warn("Error during shutdown: {}", e.getMessage());
        }
    }
}