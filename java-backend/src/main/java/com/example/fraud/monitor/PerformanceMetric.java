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
    // Required for constructor.
    private static final int UPDATE_FREQUENCY = 5;
    private static final int WINDOW_SIZE = 10 * 60 / UPDATE_FREQUENCY; // 10 minutes * 60 seconds / update every 5 seconds
    final int maxHistory;

    // Default info required.
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
            ruleMetrics[index.incrementAndGet() % maxHistory] = new PerfMetric(
                    perfInfo.totalTime().toMillis(),
                    perfInfo.isSuccessful(),
                    perfInfo.start(),
                    storedTime);

            final Long startTimeSeconds = perfInfo.start().getEpochSecond() / 5;
            final int startTimeWindowFrame = (int) (startTimeSeconds % WINDOW_SIZE);
            synchronized (PerformanceSummary.class) {
                if (transactionPerSecond[startTimeWindowFrame] == null) {
                    transactionPerSecond[startTimeWindowFrame] = new Window(startTimeSeconds);
                }
                final Window window = transactionPerSecond[startTimeWindowFrame];
                final Long startTime = window.getStartTime();
                if (startTime == null || startTime != startTimeWindowFrame) {
                    transactionPerSecond[startTimeWindowFrame] = new Window(startTimeSeconds);
                }
                window.setExecutionTimeMs(perfInfo.totalTime().toMillis());
            }
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

    public MetricInfo getMetricInfo() {
        long min = Long.MAX_VALUE;
        long max = Long.MIN_VALUE;
        long sum = 0L;
        long entries = 0L;
        long firstValidTimeSeconds = Long.MAX_VALUE;
        long lastTimeSeconds = Long.MIN_VALUE;
        long startTimeSeconds = Instant.now().getEpochSecond() / 5; // Current time in 5 second ticks.
        long earliestValidTime = startTimeSeconds - WINDOW_SIZE;
        for (final Window window : transactionPerSecond) {
            if (window.getStartTime() < earliestValidTime) {
                continue;
            }
            firstValidTimeSeconds = Math.min(window.getStartTime() * 5, firstValidTimeSeconds);
            lastTimeSeconds = Math.max(lastTimeSeconds, window.getStartTime());
            min = Math.min(window.minTime, min);
            max = Math.max(window.maxTime, max);
            sum += window.executionTimes.stream().reduce(0L, Long::sum);
            entries += window.executionTimes.size();
        }
        if (lastTimeSeconds == firstValidTimeSeconds) {
            // avoid divide by 0.
            return new MetricInfo(min, max, sum / entries, entries);
        } else {
            return new MetricInfo(min, max, sum / entries, entries / (lastTimeSeconds - firstValidTimeSeconds));
        }
    }

    public record MetricInfo(Long min, Long max, Long avg, Long qps) {
    }

    @Getter
    private static class Window {
        final Long startTime;
        final AtomicInteger queryCounter = new AtomicInteger();
        Long minTime = Long.MAX_VALUE;
        Long maxTime = -1L;
        final List<Long> executionTimes = new ArrayList<>();

        public Window(final Long startTime) {
            this.startTime = startTime;
        }

        public Long getStartTime() {
            return this.startTime;
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
