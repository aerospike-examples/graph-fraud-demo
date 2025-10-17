package com.example.fraud.monitor;

import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.fraud.TransactionSummary;
import com.example.fraud.rules.Rule;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class PerformanceSummary {
    // Rule specific info.
    private static final Logger log = LoggerFactory.getLogger("fraud_detection.performance");
    final Map<String, PerformanceMetric> ruleNameToPerformanceInfo = new HashMap<>();
    final PerformanceMetric transactionPerformanceInfo;

    //debug var
    final AtomicInteger transactionsCount = new AtomicInteger(0);
    public PerformanceSummary(final List<Rule> rules, final int maxHistory) {
        for (final Rule rule : rules) {
            ruleNameToPerformanceInfo.put(rule.getName(), new PerformanceMetric(maxHistory));
        }
        transactionPerformanceInfo = new PerformanceMetric(maxHistory);
    }

    public void updateAsyncPerformance(final TransactionSummary summary) {
        final Instant storedTime = Instant.now();
        for (final FraudResult result: summary.fraudOutcomes()) {
            updatePerformanceForName(result.details().ruleName(), result, storedTime);
        }
    }

    public void updatePerformance(final TransactionSummary summary) {
        final Instant storedTime = Instant.now();
        updatePerformanceForTransaction(summary.transactionInfo(), storedTime);
        for (final FraudResult result: summary.fraudOutcomes()) {
            updatePerformanceForName(result.details().ruleName(), result, storedTime);
        }
    }

    private void updatePerformanceForName(final String name, final FraudResult result, final Instant storedTime) {
        final PerformanceMetric performanceInfo = ruleNameToPerformanceInfo.get(name);
        performanceInfo.insertMetric(result.performanceInfo(), storedTime);
    }

    private void updatePerformanceForTransaction(final TransactionInfo transactionInfo, final Instant storedTime) {
        transactionPerformanceInfo.insertMetric(transactionInfo.performanceInfo(), storedTime);
    }

    public long getTotalFailed() {
        long totalFailed = 0;
        for (final PerformanceMetric performanceInfo : ruleNameToPerformanceInfo.values()) {
            totalFailed += performanceInfo.getFailureCount();
        }
        return totalFailed;
    }

    public long getTotalSuccess() {
        long totalSuccess = 0;
        for (final PerformanceMetric performanceInfo : ruleNameToPerformanceInfo.values()) {
            totalSuccess += performanceInfo.getSuccessCount();
        }
        return totalSuccess;
    }

    public void reset() {
        synchronized (PerformanceSummary.class) {
            for (PerformanceMetric metric : ruleNameToPerformanceInfo.values()) {
                metric.reset();
            }
            transactionPerformanceInfo.reset();
        }
    }
}
