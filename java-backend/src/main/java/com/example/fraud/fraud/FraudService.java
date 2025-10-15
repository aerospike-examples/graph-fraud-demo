package com.example.fraud.fraud;

import com.example.fraud.config.FraudProperties;
import com.example.fraud.model.FraudCheckStatus;
import com.example.fraud.monitor.PerformanceMonitor;
import com.example.fraud.graph.GraphService;
import com.example.fraud.rules.Rule;
import java.util.concurrent.atomic.AtomicInteger;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

@Service
public class FraudService {

    private static final Logger log = LoggerFactory.getLogger("fraud_detection.fraud");
    private final GraphService graph;
    private final PerformanceMonitor perf;
    private final ExecutorService exec;
    private final List<Rule> fraudRulesList;
    private final Map<String, Rule> fraudRulesMap;
    private final FraudProperties props;

    public FraudService(GraphService graphService, PerformanceMonitor performanceMonitor,
                        List<Rule> fraudRulesList, FraudProperties props) {
        this.graph = graphService;
        this.perf = performanceMonitor;
        this.fraudRulesList = fraudRulesList;
        Map <String, Rule> fraudRulesMap = new HashMap<String,Rule>();
        for (Rule r : fraudRulesList) {
            fraudRulesMap.put(r.getName(), r);
        }
        this.props = props;
        this.fraudRulesMap = fraudRulesMap;
        this.exec = new ThreadPoolExecutor(
                props.getFraudWorkerPoolSize(), props.getFraudWorkerMaxPoolSize(),
                60L, TimeUnit.SECONDS,
                new SynchronousQueue<>(),
                new NamedFactory("fraud"),
                new ThreadPoolExecutor.CallerRunsPolicy());
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

    public Map<String, Boolean> getFraudChecksState() {
        final Map<String, Boolean> m = new LinkedHashMap<>(fraudRulesMap.size());

        for (final Map.Entry<String, Rule> pair : fraudRulesMap.entrySet()) {
            m.put(pair.getKey(), pair.getValue().isEnabled());
        }
        return m;
    }

    public void submitFraudDetection(final TransactionInfo transactionInfo) {
        exec.submit(() -> runFraudDetection(transactionInfo));
    }
    public TransactionSummary runFraudDetection(final TransactionInfo txnInfo) {
        long startTime = System.nanoTime();

        final GraphTraversalSource fraudG = graph.getFraudClient();
        if (fraudG == null) {
            log.warn("Graph client not available for fraud detection");
            return new TransactionSummary(List.of(), txnInfo);
        }

        final List<FraudResult> fraudOutcomes = new ArrayList<>();
        for (final Rule rule : fraudRulesList) {
            if (!rule.isEnabled()) continue;
            fraudOutcomes.add(rule.executeRule(txnInfo));
        }
        final TransactionSummary summary = new TransactionSummary(fraudOutcomes, txnInfo);
        storeFraudResults(graph.getMainClient(), txnInfo.edgeId(), summary);
        perf.recordTransactionCompletedDetailed(summary);

        return summary;
    }

    private void storeFraudResults(GraphTraversalSource mainG, Object edgeId,
                                   TransactionSummary fraudChecks) {
        for (FraudResult check : fraudChecks.fraudOutcomes()) {
            if (check == null || !check.isFraud()) continue;
            storeFraudResult(mainG, edgeId, check);
        }
    }

    private void storeFraudResult(GraphTraversalSource g, Object edgeId, FraudResult check) {
        int fraudScore = 0;
        String status = "review";
        List<String> details = new ArrayList<>();

        Object s = check.fraudScore();
        int score = (s instanceof Number) ? ((Number) s).intValue() : 0;
        if (score > fraudScore) fraudScore = score;

        Object st = check.status();
        if (st.equals(FraudCheckStatus.BLOCKED)) status = "blocked";

        Object det = check.details();
        details.add(String.valueOf(det));

        g.E(edgeId)
                .property("is_fraud", true)
                .property("fraud_score", fraudScore)
                .property("fraud_status", status)
                .property("eval_timestamp", Instant.now().toString())
                .property("details", details)
                .iterate();
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
