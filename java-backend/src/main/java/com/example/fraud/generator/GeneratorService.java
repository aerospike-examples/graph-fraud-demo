package com.example.fraud.generator;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.graph.GraphService;
import com.example.fraud.monitor.PerformanceMonitor;
import java.util.concurrent.ThreadLocalRandom;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class GeneratorService {

    private static final Logger logger = LoggerFactory.getLogger(GeneratorService.class);
    private static final Logger statsLogger = LoggerFactory.getLogger("fraud_detection.stats");

    private final GraphService graphService;
    private final WarmupService warmupService;
    private final FraudService fraudService;
    private final PerformanceMonitor performanceMonitor;
    private final boolean WARMUP_ENABLED = true;
    private final List<String> normalLocations = Arrays.asList(
            "New York, New York", "Los Angeles, California", "Chicago, Illinois", "Houston, Texas",
            "Phoenix, Arizona", "Philadelphia, Pennsylvania", "San Antonio, Texas", "San Diego, California",
            "Dallas, Texas", "San Jose, California", "Austin, Texas", "Jacksonville, Florida",
            "Fort Worth, Texas", "Columbus, Ohio", "Charlotte, North Carolina", "San Francisco, California",
            "Indianapolis, Indiana", "Seattle, Washington", "Denver, Colorado", "Washington, District of Columbia",
            "Boston, Massachusetts", "El Paso, Texas", "Nashville, Tennessee", "Detroit, Michigan",
            "Oklahoma City, Oklahoma", "Portland, Oregon", "Las Vegas, Nevada", "Memphis, Tennessee",
            "Louisville, Kentucky", "Baltimore, Maryland", "Milwaukee, Wisconsin", "Albuquerque, New Mexico",
            "Tucson, Arizona", "Fresno, California", "Sacramento, California", "Mesa, Arizona",
            "Kansas City, Missouri", "Atlanta, Georgia", "Long Beach, California", "Colorado Springs, Colorado",
            "Raleigh, North Carolina", "Miami, Florida", "Virginia Beach, Virginia", "Omaha, Nebraska",
            "Oakland, California", "Minneapolis, Minnesota", "Tulsa, Oklahoma", "Arlington, Texas"
    );
    private final List<String> transactionTypes = Arrays.asList(
            "purchase", "transfer", "withdrawal", "deposit", "payment"
    );
    private volatile boolean isRunning = false;
    private List<Object> accountVertices = new ArrayList<>();
    private TransactionWorker transactionWorker;
    private TransactionScheduler transactionScheduler;
    private boolean WARM = false;

    public GeneratorService(GraphService graphService,
                            FraudService fraudService,
                            PerformanceMonitor performanceMonitor,
                            int transactionWorkerPoolSize, int transactionWorkerMaxPoolSize) {
        this.graphService = graphService;
        this.fraudService = fraudService;
        this.performanceMonitor = performanceMonitor;
        this.warmupService = new WarmupService(graphService, this, fraudService);
        this.transactionWorker = new TransactionWorker(this, fraudService, performanceMonitor,
                transactionWorkerPoolSize, transactionWorkerMaxPoolSize);
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
            performanceMonitor.resetTransactionMetrics();

            isRunning = true;

            if (!WARM && WARMUP_ENABLED) {
                logger.debug("Warmup Started");
                statsLogger.debug("START: Warmup starteqd");
                WARM = warmupService.runWithCleanup();
                if (WARM) {
                    logger.debug("Generator is now warmed up!");
                } else {
                    logger.error("Warmup Failed");
                    throw new RuntimeException("Error warming up generator");
                }
            }

            boolean success = transactionScheduler.startGeneration(rate);
            logger.info("Starting up generator at {} transactions/second", rate);
            performanceMonitor.setGenerationState(true, rate, 0);

            if (!success) {
                performanceMonitor.setGenerationState(false, 0, 0);
                isRunning = false;
                return false;
            }


            return true;

        } catch (Exception e) {
            logger.error("Error starting transaction generation: {}", e.getMessage());
            isRunning = false;
            performanceMonitor.setGenerationState(false, 0, 0);
            return false;
        }
    }

    public void stopGeneration() {
        if (!isRunning) {
            logger.warn("Transaction generation is not running");
            return;
        }

        isRunning = false;

        if (transactionScheduler != null) {
            transactionScheduler.stopGeneration();
        }
        if (transactionWorker != null) {
            transactionWorker.stopWorkers();
        }
        performanceMonitor.setGenerationState(false, 0, 0);

        logger.info("Transaction generation stopped");
        statsLogger.info("STOP: Generation stopped.");
    }

    public TransactionInfo generateTransaction() {
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

            double amount = 100.0 + rand.nextDouble() * 14900.0;
            String transactionType = transactionTypes.get(rand.nextInt(transactionTypes.size()));
            String location = normalLocations.get(rand.nextInt(normalLocations.size()));

            final TransactionInfo result = graphService.createTransaction(
                    senderAccountId.toString(),
                    receiverAccountId.toString(),
                    amount,
                    transactionType,
                    "AUTO",
                    location
            );

            return result;

        } catch (Exception e) {
            logger.error("Error generating normal transaction: {}", e.getMessage());
            throw new RuntimeException(e);
        }
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