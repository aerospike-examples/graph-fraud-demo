package com.example.fraud.fraud;

import java.time.Duration;
import java.time.Instant;

public record PerformanceInfo
        (Instant start,
         Duration totalTime,
         boolean isSuccessful) {
}

