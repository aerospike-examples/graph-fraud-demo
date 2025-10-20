package com.example.fraud.monitor;

import com.example.fraud.fraud.TransactionSummary;
import com.example.fraud.generator.GeneratorStatus;
import com.example.fraud.rules.Rule;
import lombok.Getter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import jakarta.annotation.PreDestroy;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.stereotype.Service;

@Service
public class PerformanceMonitor {

    private static final Logger log = LoggerFactory.getLogger("fraud_detection.performance");
    private final ExecutorService bg = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "perf_background");
        t.setDaemon(true);
        return t;
    });
    @Getter
    private GeneratorStatus generatorStatus;
    private final PerformanceSummary performanceSummary;

    private int transactionsMade = 0;


    public PerformanceMonitor(final List<Rule> rules) {
        int maxHistory = 1_000_000;
        this.performanceSummary = new PerformanceSummary(rules, maxHistory);
        log.info("Async Performance monitor initialized (maxHistory={})", maxHistory);
        generatorStatus = new GeneratorStatus(false, 0, null);
    }

    private static long nowEpochSec() {
        return Instant.now().getEpochSecond();
    }

    public void recordTransactionCompletedDetailed(final TransactionSummary summary) {
        if (transactionsMade % 200 == 0) {
            log.debug("Transaction completed ({})", summary);
        }
        transactionsMade++;
        bg.submit(() -> performanceSummary.updatePerformance(summary));
    }

    public void recordAsyncRulesCompletedDetailed(final TransactionSummary summary) {
        if (transactionsMade % 200 == 0) {
            log.debug("Transaction completed ({})", summary);
        }
        transactionsMade++;
        bg.submit(() -> performanceSummary.updateAsyncPerformance(summary));
    }

    public void setGenerationState(boolean running, int targetTps, Instant startTimeEpochSec) {
        generatorStatus = new GeneratorStatus(running, targetTps, startTimeEpochSec);
    }

    public void resetPerformanceSummary() {
        performanceSummary.reset();
    }

    private Map<String, Object> getMetricInfo(final PerformanceMetric metric, int minutes) {
        PerformanceMetric.MetricInfo info = metric.getMetricInfo(minutes);
        Long elapsed;
        if (generatorStatus.startTime() != null) {
            elapsed = nowEpochSec() - generatorStatus.startTime().getEpochSecond();
        } else {
            elapsed = 0L;
        }
        return Map.of(
                "average", info.avg(),
                "max", info.max(),
                "min", info.min(),
                "total_success", metric.getSuccessCount(),
                "total_failure", metric.getFailureCount(),
                "QPS", info.qps(),
                "elapsed_time_seconds", elapsed
        );
    }

    public Map<String, Object> getAllStats(int minutes) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("timestamp", Instant.now().toString());
        out.put("is_running", generatorStatus.running());
        out.put("transaction_stats", getMetricInfo(performanceSummary.transactionPerformanceInfo, minutes));
        for (final Map.Entry<String, PerformanceMetric> rulePerf : performanceSummary.ruleNameToPerformanceInfo.entrySet()) {
            out.put(rulePerf.getKey(), getMetricInfo(rulePerf.getValue(), minutes));
        }
        return out;
    }

    @PreDestroy
    public void shutdown() {
        bg.shutdown();
        try {
            if (!bg.awaitTermination(3, TimeUnit.SECONDS)) {
                bg.shutdownNow();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
