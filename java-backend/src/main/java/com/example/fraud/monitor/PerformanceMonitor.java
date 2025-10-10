package com.example.fraud.monitor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import jakarta.annotation.PreDestroy;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.stream.Collectors;

public class PerformanceMonitor {

    private static final Logger log = LoggerFactory.getLogger("fraud_detection.performance");

    private final ExecutorService bg = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "perf_background");
        t.setDaemon(true);
        return t;
    });

    private final int maxHistory;
    private final ConcurrentLinkedDeque<MethodMetric> rt1Metrics = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<MethodMetric> rt2Metrics = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<MethodMetric> rt3Metrics = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<TxnMetric> txnMetrics = new ConcurrentLinkedDeque<>();
    private final AtomicInteger rt1Size = new AtomicInteger(0);
    private final AtomicInteger rt2Size = new AtomicInteger(0);
    private final AtomicInteger rt3Size = new AtomicInteger(0);
    private final AtomicInteger txnSize = new AtomicInteger(0);

    private final LongAdder rt1Counter = new LongAdder();
    private final LongAdder rt2Counter = new LongAdder();
    private final LongAdder rt3Counter = new LongAdder();

    private final LongAdder rt1Success = new LongAdder();
    private final LongAdder rt1Failure = new LongAdder();
    private final LongAdder rt2Success = new LongAdder();
    private final LongAdder rt2Failure = new LongAdder();
    private final LongAdder rt3Success = new LongAdder();
    private final LongAdder rt3Failure = new LongAdder();

    private final LongAdder totalScheduled = new LongAdder();
    private final LongAdder totalCompleted = new LongAdder();
    private final LongAdder totalFailed = new LongAdder();

    private final ConcurrentLinkedDeque<Double> latenciesMs = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<Double> execLatenciesMs = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<Double> queueWaitMs = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<Double> dbLatenciesMs = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<Double> fraudLatenciesMs = new ConcurrentLinkedDeque<>();
    private final ConcurrentLinkedDeque<Long> completionTimesEpochSec = new ConcurrentLinkedDeque<>();

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

    public void setGenerationState(boolean running, double targetTps, int queueSize) {
        readLock.lock();
        try {
            this.isRunning = running;
            this.targetTps = targetTps;
            this.queueSize = queueSize;

            if (running && startTimeEpochSec == 0L) {
                startTimeEpochSec = nowEpochSec();
            } else if (!running && startTimeEpochSec != 0L) {
                elapsedTimeSec = (double) (nowEpochSec() - startTimeEpochSec);
            }
        } finally {
            readLock.unlock();
        }
    }

    public void resetTransactionMetrics() {
        readLock.lock();
        try {
            txnMetrics.clear();
            totalScheduled.reset();
            totalCompleted.reset();
            totalFailed.reset();
            completionTimesEpochSec.clear();
            latenciesMs.clear();
            execLatenciesMs.clear();
            startTimeEpochSec = 0L;
            elapsedTimeSec = 0.0;
            currentTps = 0.0;
        } finally {
            readLock.unlock();
        }
    }

    public void resetMetrics() {
        readLock.lock();
        try {
            rt1Metrics.clear();
            rt2Metrics.clear();
            rt3Metrics.clear();
            rt1Counter.reset();
            rt2Counter.reset();
            rt3Counter.reset();
            rt1Success.reset();
            rt1Failure.reset();
            rt2Success.reset();
            rt2Failure.reset();
            rt3Success.reset();
            rt3Failure.reset();

            txnMetrics.clear();
            totalScheduled.reset();
            totalCompleted.reset();
            totalFailed.reset();
            completionTimesEpochSec.clear();
            latenciesMs.clear();
            execLatenciesMs.clear();
            queueWaitMs.clear();
            dbLatenciesMs.clear();
            fraudLatenciesMs.clear();
            startTimeEpochSec = 0L;
            elapsedTimeSec = 0.0;
            currentTps = 0.0;
        } finally {
            readLock.unlock();
        }
        log.info("Performance metrics reset");
    }

    public Map<String, Object> getTransactionStats() {
        readLock.lock();
        try {
            double avgLatency = avg(latenciesMs);
            double minLatency = min(latenciesMs);
            double maxLatency = max(latenciesMs);

            double avgExec = avg(execLatenciesMs);
            double minExec = min(execLatenciesMs);
            double maxExec = max(execLatenciesMs);

            if (startTimeEpochSec != 0L && isRunning) {
                elapsedTimeSec = (double) (nowEpochSec() - startTimeEpochSec);
            } else if (!isRunning && elapsedTimeSec == 0.0) {
                elapsedTimeSec = 0.0;
            }

            double completed = totalCompleted.doubleValue();
            double scheduled = Math.max(1.0, totalScheduled.doubleValue());
            double actualTps = elapsedTimeSec > 0.0 ? completed / Math.max(0.01, elapsedTimeSec) : 0.0;
            double successRate = (completed / scheduled) * 100.0;

            double avgQueueWait = avg(queueWaitMs);
            double minQueueWait = min(queueWaitMs);
            double maxQueueWait = max(queueWaitMs);

            double avgDb = avg(dbLatenciesMs);
            double minDb = min(dbLatenciesMs);
            double maxDb = max(dbLatenciesMs);

            double avgFraud = avg(fraudLatenciesMs);
            double minFraud = min(fraudLatenciesMs);
            double maxFraud = max(fraudLatenciesMs);

            Map<String, Object> out = new LinkedHashMap<>();
            out.put("is_running", isRunning);
            out.put("target_tps", targetTps);
            out.put("current_tps", currentTps);
            out.put("actual_tps", actualTps);
            out.put("elapsed_time", elapsedTimeSec);
            out.put("total_scheduled", (long) totalScheduled.sum());
            out.put("total_completed", (long) totalCompleted.sum());
            out.put("total_failed", (long) totalFailed.sum());
            out.put("queue_size", queueSize);

            out.put("avg_latency_ms", avgLatency);
            out.put("min_latency_ms", minLatency);
            out.put("max_latency_ms", maxLatency);

            out.put("avg_exec_latency_ms", avgExec);
            out.put("min_exec_latency_ms", minExec);
            out.put("max_exec_latency_ms", maxExec);

            out.put("success_rate", successRate);

            out.put("avg_queue_wait_ms", avgQueueWait);
            out.put("min_queue_wait_ms", minQueueWait);
            out.put("max_queue_wait_ms", maxQueueWait);

            out.put("avg_db_latency_ms", avgDb);
            out.put("min_db_latency_ms", minDb);
            out.put("max_db_latency_ms", maxDb);

            out.put("avg_fraud_latency_ms", avgFraud);
            out.put("min_fraud_latency_ms", minFraud);
            out.put("max_fraud_latency_ms", maxFraud);

            return out;
        } finally {
            readLock.unlock();
        }
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

    public Map<String, List<Map<String, Object>>> getRecentTimelineData(int minutes) {
        Instant cutoff = Instant.now().minus(Duration.ofMinutes(minutes));
        readLock.lock();
        try {
            List<Map<String, Object>> rt1 = rt1Metrics.stream()
                    .filter(m -> !m.timestamp().isBefore(cutoff))
                    .map(m -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("timestamp", m.timestamp().toString());
                        row.put("execution_time", m.executionTimeMs());
                        row.put("method", "RT1");
                        return row;
                    })
                    .collect(Collectors.toList());

            List<Map<String, Object>> rt2 = rt2Metrics.stream()
                    .filter(m -> !m.timestamp.isBefore(cutoff))
                    .map(m -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("timestamp", m.timestamp().toString());
                        row.put("execution_time", m.executionTimeMs());
                        row.put("method", "RT2");
                        return row;
                    }).collect(Collectors.toList());

            List<Map<String, Object>> rt3 = rt3Metrics.stream()
                    .filter(m -> !m.timestamp.isBefore(cutoff))
                    .map(m -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("timestamp", m.timestamp().toString());
                        row.put("execution_time", m.executionTimeMs());
                        row.put("method", "RT3");
                        return row;
                    }).collect(Collectors.toList());

            Map<String, List<Map<String, Object>>> out = new LinkedHashMap<>();
            out.put("rt1", rt1);
            out.put("rt2", rt2);
            out.put("rt3", rt3);
            return out;
        } finally {
            readLock.unlock();
        }
    }

    private Map<String, Object> getMethodStats(ConcurrentLinkedDeque<MethodMetric> metrics, int minutes, String method) {
        Instant cutoff = Instant.now().minus(Duration.ofMinutes(minutes));
        List<MethodMetric> recent = metrics.stream()
                .filter(m -> !m.timestamp().isBefore(cutoff))
                .toList();

        if (recent.isEmpty()) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("method", method);
            empty.put("avg_execution_time", 0.0);
            empty.put("max_execution_time", 0.0);
            empty.put("min_execution_time", 0.0);
            empty.put("total_queries", 0);
            empty.put("success_rate", 0.0);
            empty.put("queries_per_second", 0.0);
            empty.put("cache_enabled", cacheStatus(method));
            return empty;
        }

        double avg = recent.stream().mapToDouble(m -> m.executionTimeMs).average().orElse(0.0);
        double max = recent.stream().mapToDouble(m -> m.executionTimeMs).max().orElse(0.0);
        double min = recent.stream().mapToDouble(m -> m.executionTimeMs).min().orElse(0.0);
        long successCount = recent.stream().filter(m -> m.success).count();

        double timeSpanSec = (double) Duration.between(cutoff, Instant.now()).toMillis() / 1000.0;
        double qps = timeSpanSec > 0 ? (recent.size() / timeSpanSec) : 0.0;

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("method", method);
        out.put("avg_execution_time", round2(avg));
        out.put("max_execution_time", round2(max));
        out.put("min_execution_time", round2(min));
        out.put("total_queries", recent.size());
        out.put("success_rate", round1((successCount * 100.0) / recent.size()));
        out.put("queries_per_second", round2(qps));
        out.put("cache_enabled", cacheStatus(method));
        return out;
    }

    private void updateCurrentTps() {
        long now = nowEpochSec();
        long recent = completionTimesEpochSec.stream().filter(t -> now - t <= 1).count();
        currentTps = (double) recent;
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
