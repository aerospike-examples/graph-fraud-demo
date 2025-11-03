package com.example.fraud.fraud;

import com.example.fraud.config.FraudProperties;
import com.example.fraud.metadata.AerospikeMetadataManager;
import com.example.fraud.model.AutoFlagMode;
import com.example.fraud.model.FraudCheckStatus;
import com.example.fraud.model.MetadataRecord;
import com.example.fraud.monitor.PerformanceMonitor;
import com.example.fraud.graph.GraphService;
import com.example.fraud.rules.Rule;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.concurrent.atomic.AtomicInteger;
import lombok.Getter;
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
    @Getter
    private final List<Rule> fraudRulesList;
    private final Map<String, Rule> fraudRulesMap;
    private final FraudProperties props;
    private final GraphService graphService;
    private final AerospikeMetadataManager metadataManager;
    private final RecentTransactions recentTransactions;

    public FraudService(PerformanceMonitor performanceMonitor,
                        List<Rule> fraudRulesList, FraudProperties props,
                        GraphService graphService, AerospikeMetadataManager metadataManager,
                        RecentTransactions recentTransactions) {
        this.graph = graphService;
        this.perf = performanceMonitor;
        Map<String, Rule> fraudRulesMap = new HashMap<String, Rule>();
        for (Rule r : fraudRulesList) {
            fraudRulesMap.put(r.getName(), r);
        }
        this.props = props;
        this.fraudRulesList = fraudRulesList;
        this.fraudRulesMap = fraudRulesMap;
        this.exec = Executors.newFixedThreadPool(props.getFraudWorkerPoolSize(), new NamedFactory("fraud"));
        this.graphService = graphService;
        this.metadataManager = metadataManager;
        this.recentTransactions = recentTransactions;
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

    public boolean setRuleEnabled(String name, boolean enabled) {
        Rule r = fraudRulesMap.get(name);
        if (r == null) return false;
        r.setEnabled(enabled);
        log.info("Rule '{}' enabled set to {}", name, enabled);
        return true;
    }

    public void submitFraudDetection(final TransactionInfo transactionInfo) {
        final List<Future<FraudResult>> futures = new ArrayList<>();
        for (final Rule rule : fraudRulesList) {
            if (rule.isEnabled()) {
                futures.add(exec.submit(() -> rule.executeRule(transactionInfo)));
            }
        }
        final List<FraudResult> results = new ArrayList<>();
        for (final Future<FraudResult> future : futures) {
            try {
                results.add(future.get());
            } catch (InterruptedException | ExecutionException e) {
                futures.forEach(ff -> ff.cancel(true));
                Thread.currentThread().interrupt();
            } catch (CancellationException ce) {
                log.debug("Fraud check cancelled (shutdown in progress)");
                return;
            } catch (final Exception e) {
                log.error("Encountered exception while waiting for async rule to complete.", e);
                throw new RuntimeException(e);
            }
        }
        final TransactionSummary summary = new TransactionSummary(results, transactionInfo);
        storeFraudResults(graph.getMainClient(), transactionInfo.edgeId(), summary);
        recentTransactions.add(transactionInfo.edgeId());
        perf.recordTransactionCompletedDetailed(summary);
    }

    private void storeFraudResults(GraphTraversalSource mainG, Object edgeId,
                                   TransactionSummary fraudChecks) {
        boolean fraud = false;
        FraudCheckStatus status = FraudCheckStatus.CLEARED;
        for (FraudResult check : fraudChecks.fraudOutcomes()) {
            if (check == null || !check.isFraud()) continue;
            FraudCheckStatus newStatus = storeFraudResult(mainG, edgeId, check);
            if (status.lte(newStatus)) {
                status = newStatus;
            }
            fraud = true;
        }
        if (fraud) {
            metadataManager.incrementCount(MetadataRecord.FRAUD, status.getValue(), 1);
        }


    }

    private FraudCheckStatus storeFraudResult(GraphTraversalSource g, Object edgeId, FraudResult check) {
        int fraudScore = 0;
        String status = check.status().getValue();
        Number s = check.fraudScore();
        int score = s.intValue();
        if (score > fraudScore) fraudScore = score;

        FraudCheckDetails details = check.details();
        LocalDateTime detectionTime = LocalDateTime.ofInstant(details.detectionTime(), ZoneId.systemDefault());
        Map<Object, Object> curr = g.E(edgeId).valueMap("is_fraud", "fraud_score").next();
        if ((int) curr.getOrDefault("fraud_score", 0) < fraudScore) {
            g.E(edgeId)
                    .property("is_fraud", true)
                    .property("fraud_score", fraudScore)
                    .property("fraud_status", status)
                    .property("eval_timestamp", Instant.now().toString())
                    .property("rule_name", details.ruleName())
                    .property("detection_time", detectionTime.toString())
                    .iterate();

            if (props.isAutoFlagEnabled()) {
                AutoFlagMode mode = props.getAutoFlagMode();
                switch (mode) {
                    case AutoFlagMode.SENDER -> {
                        graphService.flagAccount(check.details().sender(), check.reason());
                    }
                    case AutoFlagMode.RECEIVER -> {
                        graphService.flagAccount(check.details().receiver(), check.reason());
                    }
                    default -> {
                        // Assume Both
                        graphService.flagAccount(check.details().sender(), check.reason());
                        graphService.flagAccount(check.details().receiver(), check.reason());
                    }
                }
            }
        }
        return check.status();
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
