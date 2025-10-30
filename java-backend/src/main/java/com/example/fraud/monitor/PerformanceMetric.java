package com.example.fraud.monitor;

import com.example.fraud.fraud.PerformanceInfo;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.LongAdder;
import lombok.Getter;

public class PerformanceMetric {
    private static final int UPDATE_FREQUENCY = 5;
    private static final int WINDOW_SIZE = 10 * 60 / UPDATE_FREQUENCY; // 10 minutes * 60 seconds / update every 5 seconds
    final int maxHistory;

    private final Object lock = new Object();
    private PerfMetric[] ruleMetrics;
    private final LongAdder ruleSuccess = new LongAdder();
    private final LongAdder ruleFailure = new LongAdder();
    private final AtomicInteger index = new AtomicInteger(0);
    final Window[] transactionPerSecond = new Window[WINDOW_SIZE];

    public PerformanceMetric(final int maxHistory) {
        this.maxHistory = maxHistory;
        this.ruleMetrics = new PerfMetric[maxHistory];
    }

    private record PerfMetric(double executionTimeMs,
                              boolean success,
                              Instant startTime,
                              Instant storedTime) {
    }

    public void insertMetric(final PerformanceInfo perfInfo, final Instant storedTime) {
        synchronized (lock) {
            if (perfInfo.isSuccessful()) {
                ruleSuccess.increment();
            } else {
                ruleFailure.increment();
            }

            ruleMetrics[index.getAndIncrement() % maxHistory] = new PerfMetric(
                    perfInfo.totalTime().toMillis(),
                    perfInfo.isSuccessful(),
                    perfInfo.start(),
                    storedTime
            );

            final long bucket = perfInfo.start().getEpochSecond() / UPDATE_FREQUENCY; // 5-second bucket
            final int slot = (int) (bucket % WINDOW_SIZE);

            Window window = transactionPerSecond[slot];
            if (window == null || !window.getStartTime().equals(bucket)) {
                window = new Window(bucket);
                transactionPerSecond[slot] = window;
            }
            window.setExecutionTimeMs(perfInfo.totalTime().toMillis());
        }
    }

    public long getFailureCount() {
        return ruleFailure.longValue();
    }

    public long getSuccessCount() {
        return ruleSuccess.longValue();
    }

    public void reset() {
        synchronized (lock) {
            ruleSuccess.reset();
            ruleFailure.reset();
            ruleMetrics = new PerfMetric[maxHistory];
            index.set(0);
            Arrays.fill(transactionPerSecond, null);
        }
    }

    public MetricInfo getMetricInfo(int minutes) {
        long nowBucket = Instant.now().getEpochSecond() / UPDATE_FREQUENCY; // bucket index
        long lookbackBuckets = Math.max(1, (minutes * 60L) / UPDATE_FREQUENCY);
        long earliestBucket = nowBucket - lookbackBuckets + 1;

        double min = Double.MAX_VALUE, max = Double.MIN_VALUE, sum = 0d;
        long entries = 0L;
        long firstBucket = Long.MAX_VALUE, lastBucket = Long.MIN_VALUE;

        synchronized (lock) {
            for (final Window window : transactionPerSecond) {
                if (window == null) continue;
                long b = window.getStartTime(); // bucket index units
                if (b < earliestBucket) continue;

                firstBucket = Math.min(firstBucket, b);
                lastBucket = Math.max(lastBucket, b);

                min = Math.min(min, window.minTime);
                max = Math.max(max, window.maxTime);
                for (Long t : window.executionTimes) {
                    sum += t;
                    entries++;
                }
            }
        }

        if (entries == 0) return new MetricInfo(0d, 0d, 0d, 0d);
        int currentIndex = (int) (nowBucket % WINDOW_SIZE) - 1;
        if (currentIndex < 0) {
            currentIndex = WINDOW_SIZE - 1;
        }
        double qps = transactionPerSecond[currentIndex] != null ? transactionPerSecond[currentIndex].getQPS() : 0.0;
        return new MetricInfo(min, max, sum / entries, qps);
    }

    public record MetricInfo(Double min, Double max, Double avg, Double qps) {
    }

    @Getter
    private static class Window {
        final Long startTime; // bucket index
        final AtomicInteger queryCounter = new AtomicInteger();
        Long minTime = Long.MAX_VALUE;
        Long maxTime = -1L;
        final List<Long> executionTimes = new ArrayList<>();

        public Window(final Long startTime) {
            this.startTime = startTime;
        }

        public int getQPS() {
            return this.queryCounter.get() / UPDATE_FREQUENCY;
        }

        public void setExecutionTimeMs(final long executionTimeMs) {
            synchronized (queryCounter) {
                minTime = Math.min(minTime, executionTimeMs);
                maxTime = Math.max(maxTime, executionTimeMs);
                executionTimes.add(executionTimeMs);
                queryCounter.incrementAndGet();
            }
        }
    }
}
