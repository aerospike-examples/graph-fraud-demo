package com.example.fraud.monitor;

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

    private final AtomicInteger latenciesSize = new AtomicInteger(0);
    private final AtomicInteger execLatenciesSize = new AtomicInteger(0);
    private final AtomicInteger queueWaitSize = new AtomicInteger(0);
    private final AtomicInteger dbLatenciesSize = new AtomicInteger(0);
    private final AtomicInteger fraudLatenciesSize = new AtomicInteger(0);
    private final AtomicInteger completionTimesSize = new AtomicInteger(0);

    private final ReentrantReadWriteLock rwl = new ReentrantReadWriteLock();
    private final ReentrantReadWriteLock.ReadLock readLock = rwl.readLock();

    private volatile boolean isRunning = false;
    private volatile double targetTps = 0.0;
    private volatile double currentTps = 0.0;
    private volatile long startTimeEpochSec = 0L;   // 0 means not started
    private volatile double elapsedTimeSec = 0.0;
    private volatile int queueSize = 0;

    public PerformanceMonitor() {
        this(1_000_000);
    }

    public PerformanceMonitor(int maxHistory) {
        this.maxHistory = maxHistory;
        log.info("Async Performance monitor initialized (maxHistory={})", maxHistory);
    }

    private static String cacheStatus(String method) {
        return switch (method) {
            case "RT1" -> "Enabled (10min TTL)";
            case "RT2" -> "Disabled (real-time network)";
            case "RT3" -> "Enabled (5min TTL)";
            default -> "Unknown";
        };
    }

    private static Instant now() {
        return Instant.now();
    }

    private static long nowEpochSec() {
        return Instant.now().getEpochSecond();
    }

    private static double avg(ConcurrentLinkedDeque<Double> dq) {
        if (dq.isEmpty()) return 0.0;
        double sum = 0.0;
        int n = 0;
        for (Double d : dq) {
            sum += d;
            n++;
        }
        return n == 0 ? 0.0 : sum / n;
    }

    private static double min(ConcurrentLinkedDeque<Double> dq) {
        return dq.isEmpty() ? 0.0 : dq.stream().min(Double::compare).orElse(0.0);
    }

    private static double max(ConcurrentLinkedDeque<Double> dq) {
        return dq.isEmpty() ? 0.0 : dq.stream().max(Double::compare).orElse(0.0);
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }

    private static double round1(double v) {
        return Math.round(v * 10.0) / 10.0;
    }

    public void recordRt1Performance(double executionTimeMs, boolean success, String queryComplexity, boolean cacheHit) {
        bg.submit(() -> {
            MethodMetric metric = new MethodMetric(now(), executionTimeMs, success, queryComplexity, cacheHit, "RT1");

            rt1Metrics.offerLast(metric);

            if (rt1Size.incrementAndGet() > maxHistory) {
                rt1Metrics.pollFirst();
                rt1Size.decrementAndGet();
            }

            rt1Counter.increment();
            if (success) rt1Success.increment();
            else rt1Failure.increment();
        });
    }

    public void recordRt2Performance(double executionTimeMs, boolean success, String queryComplexity, boolean cacheHit) {
        bg.submit(() -> {
            MethodMetric metric = new MethodMetric(now(), executionTimeMs, success, queryComplexity, cacheHit, "RT2");

            rt2Metrics.offerLast(metric);
            if (rt2Size.incrementAndGet() > maxHistory) {
                rt2Metrics.pollFirst();
                rt2Size.decrementAndGet();
            }

            rt2Counter.increment();
            if (success) rt2Success.increment();
            else rt2Failure.increment();
        });
    }

    public void recordRt3Performance(double executionTimeMs, boolean success, String queryComplexity, boolean cacheHit) {
        bg.submit(() -> {
            MethodMetric metric = new MethodMetric(now(), executionTimeMs, success, queryComplexity, cacheHit, "RT3");

            rt3Metrics.offerLast(metric);
            if (rt3Size.incrementAndGet() > maxHistory) {
                rt3Metrics.pollFirst();
                rt3Size.decrementAndGet();
            }

            rt3Counter.increment();
            if (success) rt3Success.increment();
            else rt3Failure.increment();
        });
    }

    public void recordTransactionScheduled() {
        bg.submit(totalScheduled::increment);
    }

    public void recordTransactionCompletedDetailed(double totalLatencyMs, double executionLatencyMs,
                                                   double queueWaitLatencyMs, double dbLatencyMs) {
        bg.submit(() -> {
            txnMetrics.offerLast(TxnMetric.detailed(now(), totalLatencyMs, executionLatencyMs, queueWaitLatencyMs, dbLatencyMs, true));
            if (txnSize.incrementAndGet() > maxHistory) {
                txnMetrics.pollFirst();
                txnSize.decrementAndGet();
            }

            totalCompleted.increment();

            latenciesMs.offerLast(totalLatencyMs);
            if (latenciesSize.incrementAndGet() > 1000) {
                latenciesMs.pollFirst();
                latenciesSize.decrementAndGet();
            }

            execLatenciesMs.offerLast(executionLatencyMs);
            if (execLatenciesSize.incrementAndGet() > 1000) {
                execLatenciesMs.pollFirst();
                execLatenciesSize.decrementAndGet();
            }

            queueWaitMs.offerLast(queueWaitLatencyMs);
            if (queueWaitSize.incrementAndGet() > 1000) {
                queueWaitMs.pollFirst();
                queueWaitSize.decrementAndGet();
            }

            dbLatenciesMs.offerLast(dbLatencyMs);
            if (dbLatenciesSize.incrementAndGet() > 1000) {
                dbLatenciesMs.pollFirst();
                dbLatenciesSize.decrementAndGet();
            }

            completionTimesEpochSec.offerLast(nowEpochSec());
            if (completionTimesSize.incrementAndGet() > 100) {
                completionTimesEpochSec.pollFirst();
                completionTimesSize.decrementAndGet();
            }

            updateCurrentTps();
        });
    }

    public void recordTransactionFailed() {
        bg.submit(totalFailed::increment);
    }

    public void recordFraudDetectionLatency(final double fraudLatencyMs, final Object txnId) {
        bg.submit(() -> {
            fraudLatenciesMs.add(fraudLatencyMs);
            if (fraudLatencyMs > 500.0) {
                log.info("HIGH FRAUD LATENCY {}: {}ms", txnId != null ? txnId : "Unknown", String.format(Locale.US, "%.1f", fraudLatencyMs));
            }
        });
    }

    public void setGenerationState(boolean running, int targetTps, Instant startTimeEpochSec) {
        generatorStatus = new GeneratorStatus(running, targetTps, startTimeEpochSec);
    }

    public void resetPerformanceSummary() {
        performanceSummary.reset();
    }

    private Map<String, Object> getMetricInfo(final PerformanceMetric metric) {
        /* TODO - need to think about this.
            Transaction Stats:
                - Total Generated
                - Current Rate
                - Duration
                - Status

            Fraud Stats:
                - Avg
                - Max
                - Min
                - Total Success
                - Total Failure
                - QPS

             Way to enable and disable performance metrics
         */
        PerformanceMetric.MetricInfo info = metric.getMetricInfo();
        return Map.of(
                "average", info.avg(),
                "max", info.max(),
                "min", info.min(),
                "total_success", metric.getSuccessCount(),
                "total_failure", metric.getFailureCount(),
                "QPS", info.qps(),
                "elapsed_time_seconds", nowEpochSec() - startTimeEpochSec
        );
    }

    public Map<String, Object> getRt1Stats(int minutes) {
        return getMethodStats(rt1Metrics, minutes, "RT1");
    }

    public Map<String, Object> getRt2Stats(int minutes) {
        return getMethodStats(rt2Metrics, minutes, "RT2");
    }

    public Map<String, Object> getRt3Stats(int minutes) {
        return getMethodStats(rt3Metrics, minutes, "RT3");
    }

    public Map<String, Object> getAllStats(int minutes) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("rt1", getRt1Stats(minutes));
        out.put("rt2", getRt2Stats(minutes));
        out.put("rt3", getRt3Stats(minutes));
        out.put("transaction_generation", getTransactionStats());
        out.put("timestamp", Instant.now().toString());
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

    private record MethodMetric(Instant timestamp,
                                double executionTimeMs,
                                boolean success,
                                String queryComplexity,
                                boolean cacheHit,
                                String method) {
    }

    private record TxnMetric(Instant timestamp,
                             Double totalLatencyMs,
                             Double executionLatencyMs,
                             Double queueWaitLatencyMs,
                             Double dbLatencyMs,
                             boolean success,
                             String method) {
        static TxnMetric simple(Instant ts, Double total, Double exec, boolean ok) {
            return new TxnMetric(ts, total, exec, null, null, ok, "TRANSACTION_GENERATION");
        }

        static TxnMetric detailed(Instant ts, Double total, Double exec, Double queueWait, Double db, boolean ok) {
            return new TxnMetric(ts, total, exec, queueWait, db, ok, "TRANSACTION_GENERATION_DETAILED");
        }
    }
}
