package com.example.fraud.fraud;

import com.example.fraud.monitor.PerformanceMonitor;
import com.example.fraud.graph.GraphService; // expose g instances: mainClient(), fraudClient()
import java.util.concurrent.atomic.AtomicInteger;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

@Service
public class FraudService {

    private static final Logger log = LoggerFactory.getLogger("fraud_detection.fraud");

    private final GraphService graph;
    private final PerformanceMonitor perf;

    private final ExecutorService exec;

    private final AtomicBoolean rt1Enabled = new AtomicBoolean(true);
    private final AtomicBoolean rt2Enabled = new AtomicBoolean(true);
    private final AtomicBoolean rt3Enabled = new AtomicBoolean(true);

    public FraudService(GraphService graphService, PerformanceMonitor performanceMonitor,
                        int fraudPoolSize, int fraudMaxPoolSize) {
        this.graph = graphService;
        this.perf = performanceMonitor;

        this.exec = new ThreadPoolExecutor(
                fraudPoolSize, fraudMaxPoolSize, 60L, TimeUnit.SECONDS,
                new SynchronousQueue<>(),
                new NamedFactory("fraud-rt"),
                new ThreadPoolExecutor.CallerRunsPolicy());
    }

    private static FraudOutcome perfOkAndPass(PerformanceMonitor perf, long t0, int rt) {
        double ms = (System.nanoTime() - t0) / 1_000_000.0;
        switch (rt) {
            case 1 -> perf.recordRt1Performance(ms, true, "1-hop lookup", false);
            case 2 -> perf.recordRt2Performance(ms, true, "multi-hop network", false);
            case 3 -> perf.recordRt3Performance(ms, true, "multi-hop network", false);
        }
        return new FraudOutcome(false, "No flagged entities involved", null);
    }

    private static FraudOutcome perfOkAndHit(PerformanceMonitor perf, long t0, int rt,
                                             String reason, Map<String, Object> result) {
        double ms = (System.nanoTime() - t0) / 1_000_000.0;
        switch (rt) {
            case 1 -> perf.recordRt1Performance(ms, true, "1-hop lookup", false);
            case 2 -> perf.recordRt2Performance(ms, true, "multi-hop network", false);
            case 3 -> perf.recordRt3Performance(ms, true, "multi-hop network", false);
        }
        return new FraudOutcome(true, reason, result);
    }

    private static FraudOutcome perfFail(PerformanceMonitor perf, long t0, int rt, String reason) {
        double ms = (System.nanoTime() - t0) / 1_000_000.0;
        switch (rt) {
            case 1 -> perf.recordRt1Performance(ms, false, "1-hop lookup", false);
            case 2 -> perf.recordRt2Performance(ms, false, "multi-hop network", false);
            case 3 -> perf.recordRt3Performance(ms, false, "multi-hop network", false);
        }
        return new FraudOutcome(false, reason, null);
    }

    private static Map<String, Object> flaggedConnection(String accountId, String role, int score) {
        Map<String, Object> m = new LinkedHashMap<>(3);
        m.put("account_id", accountId);
        m.put("role", role);
        m.put("fraud_score", score);
        return m;
    }

    private static Map<String, Object> fraudResult(int score, String status, Map<String, Object> details) {
        Map<String, Object> m = new LinkedHashMap<>(6);
        m.put("is_fraud", true);
        m.put("fraud_score", score);
        m.put("status", status);
        m.put("eval_timestamp", Instant.now().toString());
        m.put("details", details);
        return m;
    }

    private static String asString(Object o) {
        return (o == null) ? null : String.valueOf(o);
    }

    @SuppressWarnings("unchecked")
    private static List<Object> castList(Object o) {
        if (o instanceof List<?> l) return (List<Object>) l;
        return null;
    }

    private static List<String> toStringList(List<Object> objects) {
        if (objects == null || objects.isEmpty()) return Collections.emptyList();
        List<String> out = new ArrayList<>(objects.size());
        for (Object o : objects) out.add(String.valueOf(o));
        return out;
    }

    public void shutdown() {
        try {
            log.info("Shutting down fraud service executor...");
            exec.shutdown();
            if (!exec.awaitTermination(10, TimeUnit.SECONDS)) {
                exec.shutdownNow();
            }
            log.info("Fraud service executor shutdown complete");
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            exec.shutdownNow();
        } catch (Exception e) {
            log.warn("Error shutting down fraud executor: {}", e.toString());
            exec.shutdownNow();
        }
    }

    public boolean toggleFraudCheck(String check, boolean enabled) {
        return switch (check.toLowerCase(Locale.ROOT)) {
            case "rt1" -> {
                rt1Enabled.set(enabled);
                yield true;
            }
            case "rt2" -> {
                rt2Enabled.set(enabled);
                yield true;
            }
            case "rt3" -> {
                rt3Enabled.set(enabled);
                yield true;
            }
            default -> false;
        };
    }

    public Map<String, Boolean> getFraudChecksState() {
        Map<String, Boolean> m = new LinkedHashMap<>(3);
        m.put("rt1", rt1Enabled.get());
        m.put("rt2", rt2Enabled.get());
        m.put("rt3", rt3Enabled.get());
        return m;
    }

    public Future<FraudSummary> submitFraudDetectionAsync(String edgeId, String txnId) {
        return exec.submit(() -> runFraudDetection(edgeId, txnId));
    }

    public FraudSummary runFraudDetection(String edgeId, String txnId) {
        long t0 = System.nanoTime();

        final GraphTraversalSource fraudG = graph.getFraudClient();
        if (fraudG == null) {
            log.warn("Graph client not available for fraud detection");
            return FraudSummary.empty();
        }

        final Map<String, Map<String, Object>> passingChecks = new LinkedHashMap<>(3);

        if (rt1Enabled.get()) {
            FraudOutcome rt1 = runRt1(fraudG, edgeId, txnId);
            if (rt1.isFraud()) passingChecks.put("rt1", rt1.result());
        }
        if (rt2Enabled.get()) {
            FraudOutcome rt2 = runRt2(fraudG, edgeId, txnId);
            if (rt2.isFraud()) passingChecks.put("rt2", rt2.result());
        }
        if (rt3Enabled.get()) {
            FraudOutcome rt3 = runRt3(fraudG, edgeId, txnId);
            if (rt3.isFraud()) passingChecks.put("rt3", rt3.result());
        }

        if (!passingChecks.isEmpty()) {
            try {
                storeFraudResults(graph.getMainClient(), edgeId, passingChecks);
            } catch (Exception e) {
                log.error("Error storing fraud results for txn {}: {}", txnId, e.toString());
            }
        }

        double fraudLatencyMs = (System.nanoTime() - t0) / 1_000_000.0;
        perf.recordFraudDetectionLatency(fraudLatencyMs, txnId);

        return summarize(passingChecks);
    }

    private FraudOutcome runRt1(GraphTraversalSource g, String edgeId, String txnId) {
        long t0 = System.nanoTime();
        boolean ok = true;
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> connections = (Map<String, Object>) g.E(edgeId)
                    .project("sender", "receiver")
                    .by(__.outV().has("fraud_flag", true).id())
                    .by(__.inV().has("fraud_flag", true).id())
                    .next();

            Object sender = connections.get("sender");
            Object receiver = connections.get("receiver");

            if (sender == null && receiver == null) {
                return perfOkAndPass(perf, t0, 1);
            }

            List<Map<String, Object>> flagged = new ArrayList<>(2);
            if (sender != null) flagged.add(flaggedConnection(String.valueOf(sender), "sender", 100));
            if (receiver != null) flagged.add(flaggedConnection(String.valueOf(receiver), "receiver", 100));

            int total = flagged.size();
            int score = 100;
            String reason = "Connected to " + total + " flagged account(s) - 'direct fraud'";
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("flagged_connections", flagged);
            details.put("detection_time", Instant.now().toString());
            details.put("fraud_score", score);
            details.put("reason", reason);
            details.put("rule", "RT1_SingleLevelFlaggedAccountRule");

            Map<String, Object> result = fraudResult(score, "blocked", details);
            return perfOkAndHit(perf, t0, 1, reason, result);

        } catch (Exception e) {
            ok = false;
            log.error("Error in RT1 fraud detection for txn {}: {}", txnId, e.toString());
            return perfFail(perf, t0, 1, "Detection error: " + e.getMessage());
        } finally {
            if (ok) perf.recordRt1Performance((System.nanoTime() - t0) / 1_000_000.0, true, "1-hop lookup", false);
            else perf.recordRt1Performance((System.nanoTime() - t0) / 1_000_000.0, false, "1-hop lookup", false);
        }
    }

    private FraudOutcome runRt2(GraphTraversalSource g, String edgeId, String txnId) {
        long t0 = System.nanoTime();
        boolean ok = true;
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> connections = (Map<String, Object>) g.E(edgeId)
                    .project("sender", "receiver")
                    .by(__.outV().bothE("TRANSACTS").bothV().has("fraud_flag", true).id().dedup().fold())
                    .by(__.inV().bothE("TRANSACTS").bothV().has("fraud_flag", true).id().dedup().fold())
                    .next();

            List<Object> senderList = castList(connections.get("sender"));
            List<Object> receiverList = castList(connections.get("receiver"));

            if ((senderList == null || senderList.isEmpty()) &&
                    (receiverList == null || receiverList.isEmpty())) {
                return perfOkAndPass(perf, t0, 2);
            }

            List<Map<String, Object>> flagged = new ArrayList<>(
                    (senderList != null ? senderList.size() : 0) + (receiverList != null ? receiverList.size() : 0));
            if (senderList != null) {
                for (Object o : senderList) {
                    flagged.add(flaggedConnection(String.valueOf(o), "sender_txn_partner", 75));
                }
            }
            if (receiverList != null) {
                for (Object o : receiverList) {
                    flagged.add(flaggedConnection(String.valueOf(o), "receiver_txn_partner", 75));
                }
            }

            int total = flagged.size();
            int score = Math.min(75 + total * 5, 95);
            String status = (score >= 90) ? "blocked" : "review";
            String reason = "Connected to " + total + " flagged account(s) - transaction partners";
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("flagged_connections", flagged);
            details.put("total_connections", total);
            details.put("detection_time", Instant.now().toString());
            details.put("fraud_score", score);
            details.put("reason", reason);
            details.put("rule", "RT2_MultiLevelFlaggedAccountRule");

            Map<String, Object> result = fraudResult(score, status, details);
            return perfOkAndHit(perf, t0, 2, reason, result);

        } catch (Exception e) {
            ok = false;
            log.error("Error in RT2 fraud detection for txn {}: {}", txnId, e.toString());
            return perfFail(perf, t0, 2, "Detection error: " + e.getMessage());
        } finally {
            if (ok) perf.recordRt2Performance((System.nanoTime() - t0) / 1_000_000.0, true, "multi-hop network", false);
            else perf.recordRt2Performance((System.nanoTime() - t0) / 1_000_000.0, false, "multi-hop network", false);
        }
    }

    private FraudOutcome runRt3(GraphTraversalSource g, String edgeId, String txnId) {
        long t0 = System.nanoTime();
        boolean ok = true;
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> results = (Map<String, Object>) g.E(edgeId)
                    .project("sender", "receiver", "accounts", "devices")
                    .by(__.outV().in("OWNS").id())
                    .by(__.inV().in("OWNS").id())
                    .by(__.bothV().in("OWNS").out("OWNS").both("TRANSACTS").in("OWNS").id().dedup().fold())
                    .by(__.bothV().in("OWNS").out("OWNS").both("TRANSACTS").in("OWNS").out("USES")
                            .has("fraud_flag", true).id().dedup().fold())
                    .next();

            String sender = asString(results.get("sender"));
            String receiver = asString(results.get("receiver"));
            List<String> accounts = toStringList(castList(results.get("accounts")));
            List<String> devices = toStringList(castList(results.get("devices")));

            if (devices == null || devices.isEmpty()) {
                return perfOkAndPass(perf, t0, 3);
            }

            int score = 85;
            String reason = "Transaction involves accounts connected to flagged devices in transaction network: " + String.join(", ", devices);
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("flagged_devices", devices);
            details.put("sender_account", sender);
            details.put("receiver_account", receiver);
            details.put("connected_accounts_checked", accounts != null ? accounts.size() : 0);
            details.put("detection_time", Instant.now().toString());
            details.put("fraud_score", score);
            details.put("reason", reason);
            details.put("rule", "RT3_FlaggedDeviceConnection");

            Map<String, Object> result = fraudResult(score, "review", details);
            return perfOkAndHit(perf, t0, 3, reason, result);

        } catch (Exception e) {
            ok = false;
            log.error("RT3: Error checking txn {}: {}", txnId, e.toString());
            return perfFail(perf, t0, 3, "RT3 check failed: " + e.getMessage());
        } finally {
            if (ok) perf.recordRt3Performance((System.nanoTime() - t0) / 1_000_000.0, true, "multi-hop network", false);
            else perf.recordRt3Performance((System.nanoTime() - t0) / 1_000_000.0, false, "multi-hop network", false);
        }
    }

    private void storeFraudResults(GraphTraversalSource mainG,
                                   String edgeId,
                                   Map<String, Map<String, Object>> checks) {
        int fraudScore = 0;
        String status = "review";
        List<String> details = new ArrayList<>(checks.size());

        for (Map<String, Object> check : checks.values()) {
            if (check == null || check.isEmpty()) continue;

            Object s = check.get("fraud_score");
            int score = (s instanceof Number) ? ((Number) s).intValue() : 0;
            if (score > fraudScore) fraudScore = score;

            Object st = check.get("status");
            if ("blocked".equals(st)) status = "blocked";

            Object det = check.get("details");
            details.add(String.valueOf(det));
        }

        mainG.E(edgeId)
                .property("is_fraud", true)
                .property("fraud_score", fraudScore)
                .property("fraud_status", status)
                .property("eval_timestamp", Instant.now().toString())
                .property("details", details)
                .iterate();
    }

    private FraudSummary summarize(Map<String, Map<String, Object>> checks) {
        return new FraudSummary(!checks.isEmpty(), checks);
    }

    private record FraudOutcome(boolean isFraud, String reason, Map<String, Object> result) {
    }

    public record FraudSummary(boolean anyFraud, Map<String, Map<String, Object>> checks) {
        static FraudSummary empty() {
            return new FraudSummary(false, Collections.emptyMap());
        }
    }

    private static final class NamedFactory implements ThreadFactory {
        private final String base;
        private final AtomicInteger c = new AtomicInteger(0);

        NamedFactory(String base) {
            this.base = base;
        }

        @Override
        public Thread newThread(Runnable r) {
            Thread t = new Thread(r, base + "-" + c.incrementAndGet());
            t.setDaemon(true);
            return t;
        }
    }
}
