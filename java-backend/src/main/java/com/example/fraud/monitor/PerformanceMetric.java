package com.example.fraud.monitor;

import com.example.fraud.fraud.PerformanceInfo;
import com.example.fraud.rules.ExampleRule1;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.LongAdder;
import lombok.Getter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class PerformanceMetric {
    private static final int UPDATE_FREQUENCY = 5;
    private static final int WINDOW_SIZE = 10 * 60 / UPDATE_FREQUENCY; // 10 minutes * 60 seconds / update every 5 seconds
    final int maxHistory;
    private static final Logger logger = LoggerFactory.getLogger(PerformanceMetric.class);

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

            final boolean hasTiming = perfInfo.start() != null && perfInfo.totalTime() != null;
            final Long timing = hasTiming ? perfInfo.totalTime().toMillis() : null;

            if (hasTiming && perfInfo.isSuccessful()) {
                int idx = index.getAndIncrement();
                if (idx % 1000 == 0) {
                    System.out.println("Inserting metric: " + (perfInfo.totalTime().getNano() / 1000) + " us.");
                }

                ruleMetrics[index.getAndIncrement() % maxHistory] = new PerfMetric(
                        timing,
                        true,
                        perfInfo.start(),
                        storedTime
                );
            }

            final Instant bucketInstant = perfInfo.start() != null ? perfInfo.start() : storedTime;
            final long bucket = bucketInstant.getEpochSecond() / UPDATE_FREQUENCY; // 5-second bucket
            final int slot = (int) (bucket % WINDOW_SIZE);

            Window window = transactionPerSecond[slot];
            if (window == null || !window.getStartTime().equals(bucket)) {
                window = new Window(bucket);
                transactionPerSecond[slot] = window;
            }

            window.recordCall(perfInfo.isSuccessful(), timing);
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

                if (!window.executionTimes.isEmpty()) {
                    min = Math.min(min, window.minTime);
                    max = Math.max(max, window.maxTime);
                    for (Long t : window.executionTimes) {
                        sum += t;
                        entries++;
                    }
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
        final AtomicInteger queryCounter = new AtomicInteger(); // all calls

        Long minTime = Long.MAX_VALUE;
        Long maxTime = -1L;
        final List<Long> executionTimes = new ArrayList<>();    // successful, timed calls only

        public Window(final Long startTime) {
            this.startTime = startTime;
        }

        public int getQPS() {
            return this.queryCounter.get() / UPDATE_FREQUENCY;
        }

        public void recordCall(boolean success, final Long executionTimeMs) {
            synchronized (queryCounter) {
                queryCounter.incrementAndGet();

                if (!success || executionTimeMs == null) {
                    return;
                }

                long t = executionTimeMs;
                minTime = Math.min(minTime, t);
                maxTime = Math.max(maxTime, t);
                executionTimes.add(t);
            }
        }
    }
}
