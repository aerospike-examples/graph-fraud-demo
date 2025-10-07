package com.example.fraud.generator;

import com.example.fraud.graph.GraphService;
import java.util.stream.Collectors;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;

import java.time.Instant;
import java.util.List;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class WarmupService {

    private static final Logger logger = LoggerFactory.getLogger(WarmupService.class);
    private final GraphTraversalSource g;
    private final String session = "WARMUP";
    private final int seconds = 30;
    private final int parallelism = 128;

    public WarmupService(GraphService graphService) {
        this.g = graphService.getMainClient();
    }

    private static String randomId(List<String> ids) {
        if (ids == null || ids.size() < 1) return "A0000000000000000001";
        return ids.get(ThreadLocalRandom.current().nextInt(ids.size()));
    }

    private static String pick(List<String> ids) {
        return ids.get(ThreadLocalRandom.current().nextInt(ids.size()));
    }

    private static String pickOther(List<String> ids, String not) {
        String x;
        do {
            x = pick(ids);
        } while (x.equals(not));
        return x;
    }

    public boolean runWithCleanup(List<Object> accountIds) throws InterruptedException {

        logger.info("Starting warmup");
        try {
            preOpenConnections();
            List<String> accounts = accountIds.stream()
                    .map(o -> (String) o)
                    .collect(Collectors.toList());

            runTimed(seconds / 2, () -> {
                String a = randomId(accounts);
                g.V(a).both().limit(50).values("id").iterate();
                g.V(a).bothE("TRANSACTS").limit(50).valueMap().iterate();
            });

            IntStream.range(0, 200).parallel().forEach(i -> {
                String from = pick(accounts), to = pickOther(accounts, from);
                Object eId = g.V(from).addE("TRANSACTS").to(__.V(to))
                        .property("amount", 1.00)
                        .property("gen_type", "WARMUP")
                        .property("warmup_session", session)
                        .id().next();

                Object vId = g.addV("temp_test")
                        .property("warmup_session", session)
                        .property("createdAt", Instant.now().toString())
                        .id().next();

                g.V(vId).addE("REL").to(__.V(from))
                        .property("warmup_session", session).iterate();
            });

        } finally {
            g.E().has("warmup_session", session).drop().iterate();
            g.V().has("warmup_session", session).drop().iterate();
            while (g.V().has("warmup_session", session).count().next() > 0
                    && g.E().has("warmup_session", session).count().next() > 0) {
                logger.info("Waiting for cleanup");
                Thread.sleep(1500);
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

    private void runTimed(int secs, Runnable op) {
        if (secs <= 0) return;
        Instant end = Instant.now().plusSeconds(secs);
        ForkJoinPool.commonPool().submit(() ->
                IntStream.range(0, parallelism).parallel().forEach(w -> {
                    while (Instant.now().isBefore(end)) {
                        long t0 = System.nanoTime();
                        op.run();
                    }
                })
        ).join();
    }
}
