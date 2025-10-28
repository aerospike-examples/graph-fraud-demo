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
    private final long numAccounts;
    private final int numAccountsWidth = 9;

    private final GraphService graphService;
    private final PerformanceMonitor performanceMonitor;
    private final TransactionGenerationProperties props;

    private volatile boolean isRunning = false;
    private final TransactionWorker transactionWorker;
    private final TransactionScheduler transactionScheduler;

    public GeneratorService(GraphService graphService,
                            FraudService fraudService,
                            PerformanceMonitor performanceMonitor,
                            TransactionGenerationProperties transactionGenerationProperties) {
        this.props = transactionGenerationProperties;
        this.graphService = graphService;
        this.performanceMonitor = performanceMonitor;
        this.numAccounts = this.graphService.getAccountCount();
        this.transactionWorker = new TransactionWorker(this, fraudService,
                props.getTransactionWorkerPoolSize());
        this.transactionScheduler = new TransactionScheduler(transactionWorker, performanceMonitor);
    }

    public void initializeWorkers() {
        logger.debug("Initializing transaction workers...");


        transactionWorker.startWorkers();

        logger.debug("Workers initialized and ready");
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

    public TransactionInfo generateTransaction(TransactionTask transactionTask) {
        Instant start = Instant.now();
        try {
            Object senderAccountId = randAccount();
            Object receiverAccountId = randAccount();
            while (senderAccountId.equals(receiverAccountId)) {
                receiverAccountId = randAccount();
            }


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

    private String randAccount() {
        int n = (numAccounts == Integer.MAX_VALUE)
                ? ThreadLocalRandom.current().nextInt() & 0x7fffffff
                : ThreadLocalRandom.current().nextInt((int) (numAccounts + 1));
        return padWithPrefix('A', n, numAccountsWidth);
    }

    private static int digits(int x) {
        if (x < 10) return 1;
        return 1 + (int)Math.floor(Math.log10(x));
    }

    private static String padWithPrefix(char prefix, int n, int width) {
        String s = Integer.toString(n);
        int pad = width - s.length();
        StringBuilder sb = new StringBuilder(1 + width);
        sb.append(prefix);
        for (int i = 0; i < pad; i++) sb.append('0');
        return sb.append(s).toString();
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