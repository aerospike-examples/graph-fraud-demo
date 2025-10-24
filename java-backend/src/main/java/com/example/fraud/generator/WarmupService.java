package com.example.fraud.generator;

import com.example.fraud.config.WarmupProperties;
import com.example.fraud.fraud.FraudService;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.graph.GraphService;
import com.example.fraud.model.TransactionType;
import com.example.fraud.util.FraudUtil;
import java.time.Instant;
import java.util.concurrent.ThreadLocalRandom;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;

import java.util.concurrent.ForkJoinPool;
import java.util.stream.IntStream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class WarmupService {

    private static final Logger logger = LoggerFactory.getLogger(WarmupService.class);
    private final GraphTraversalSource g;
    private final GraphService graphService;
    private final GeneratorService generatorService;
    private final FraudService fraudService;

    private final WarmupProperties props;

    public WarmupService(
            WarmupProperties warmupProperties,
            GraphService graphService,
            GeneratorService generatorService,
            FraudService fraudService) {

        this.g = graphService.getMainClient();
        this.props = warmupProperties;

        this.graphService = graphService;
        this.generatorService = generatorService;
        this.fraudService = fraudService;
    }

    public boolean runWithCleanup() {
        if (!props.isEnabled()) {
            logger.warn("Warmup is disabled");
            return true;
        }
        logger.info("Starting warmup");
        try {
            preOpenConnections();

            final long durationNanos = props.getTime().toNanos();
            final long deadlineNanos = System.nanoTime() + durationNanos;

            while (System.nanoTime() < deadlineNanos) {
                try {
                    Instant scheduledTime = Instant.now();
                    double amount = 100.0 + ThreadLocalRandom.current().nextDouble(14900.0);
                    TransactionType type = FraudUtil.getRandomTransactionType();

                    TransactionTask task = new TransactionTask(scheduledTime, amount, type);
                    TransactionInfo result = generatorService.generateTransaction(task);

                    if (result != null && result.success()) {
                        fraudService.submitFraudDetection(result);
                    }
                } catch (Exception e) {
                    logger.error("Unexpected error during warmup iteration", e);
                }
            }

            logger.debug("Finished warmup transaction creations");
        } finally {
            try {
                graphService.dropTransactions();
            } catch (InterruptedException e) {
                    throw new RuntimeException(e);
            }
        }

        logger.info("Warmup completed");
        return true;
    }

    private void preOpenConnections() {
        int ops = props.getParalellism() * 3;
        ForkJoinPool.commonPool().submit(() ->
                IntStream.range(0, ops).parallel().forEach(i -> g.inject(1).iterate())
        ).join();
    }

}
