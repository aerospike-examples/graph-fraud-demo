package com.example.fraud.generator;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.graph.GraphService;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;

import java.util.Map;
import java.util.concurrent.ForkJoinPool;
import java.util.stream.IntStream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class WarmupService {

    private static final Logger logger = LoggerFactory.getLogger(WarmupService.class);
    private final GraphTraversalSource g;
    private final GraphService graphService;
    private final GeneratorService generatorService;
    private final FraudService fraudService;
    private final int seconds = 30;
    private final int parallelism = 128;

    public WarmupService(GraphService graphService, GeneratorService generatorService, FraudService fraudService) {
        this.g = graphService.getMainClient();
        this.graphService = graphService;
        this.generatorService = generatorService;
        this.fraudService = fraudService;
    }

    public boolean runWithCleanup() throws InterruptedException {

        logger.info("Starting warmup");
        try {
            preOpenConnections();
            long end = System.nanoTime() + (long) seconds * 1_000_000_000L;
            while (System.nanoTime() < end) {
                try {
                    TransactionInfo result = generatorService.generateTransaction();
                    if (result != null && Boolean.TRUE.equals(result.get("success"))) {
                        Object edge = result.get("edge_id");
                        Object txn = result.get("txn_id");
                        if (edge instanceof String e && txn instanceof String t) {
                            fraudService.submitFraudDetectionAsync(e, t);
                        }
                    }
                } catch (Exception ignored) {
                }
            }
        logger.debug("Finished warmup transaction creations");
        } finally {
            try {
                graphService.dropTransactions();
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
            }
        }
        logger.info("Warmup completed");
        return true;
    }

    private void preOpenConnections() {
        int ops = parallelism * 3;
        ForkJoinPool.commonPool().submit(() ->
                IntStream.range(0, ops).parallel().forEach(i -> g.inject(1).iterate())
        ).join();
    }

}
