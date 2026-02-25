package com.example.fraud.generator;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

public record GeneratorStatus(
        @Schema(description = "Whether transaction generation is currently running", example = "true")
        Boolean running,
        
        @Schema(description = "Current transaction generation rate (transactions per second)", example = "100")
        Integer generationRate,
        
        @Schema(description = "Timestamp when generation started", example = "2024-01-15T10:30:45.123Z")
        Instant startTime
) {
}
