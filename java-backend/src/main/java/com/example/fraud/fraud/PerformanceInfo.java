package com.example.fraud.fraud;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Duration;
import java.time.Instant;

public record PerformanceInfo(
        @Schema(description = "Start timestamp of the operation", example = "2024-01-15T10:30:45.123Z")
        Instant start,
        
        @Schema(description = "Total duration of the operation", example = "PT0.125S")
        Duration totalTime,
        
        @Schema(description = "Whether the operation completed successfully", example = "true")
        boolean isSuccessful
) {
}

