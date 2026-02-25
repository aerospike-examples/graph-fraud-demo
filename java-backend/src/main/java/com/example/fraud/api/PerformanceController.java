package com.example.fraud.api;

import com.example.fraud.monitor.PerformanceMonitor;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.Map;

@RestController
@RequestMapping("/api/performance")
@Tag(name = "Performance Monitor", description = "Metrics on latencies, quantities, and metadata")
public class PerformanceController {

    private final PerformanceMonitor performanceMonitor;

    public PerformanceController(PerformanceMonitor performanceMonitor) {
        this.performanceMonitor = performanceMonitor;
    }

    @GetMapping("/stats")
    @ApiResponse(
        responseCode = "200",
        description = "Successfully retrieved performance statistics",
        content = @Content(
            mediaType = "application/json",
            examples = @ExampleObject(
                value = "{\"performance_stats\": {\"fraud_check_latency\": 45.5, \"transaction_creation_latency\": 23.2}, \"time_window_minutes\": 5, \"timestamp\": \"2024-01-15T10:30:45.123Z\"}"
            )
        )
    )
    public Map<String, Object> stats(
            @Parameter(description = "Time window in minutes for performance statistics (1-60)", example = "10")
            @RequestParam(name = "time_window", defaultValue = "5") @Min(1) @Max(60) int minutes) {
        var stats = performanceMonitor.getAllStats(minutes);
        return Map.of(
                "performance_stats", stats,
                "time_window_minutes", minutes,
                "timestamp", Instant.now().toString()
        );
    }

    @PostMapping("/reset")
    @ApiResponse(
        responseCode = "200",
        description = "Performance metrics reset successfully",
        content = @Content(
            mediaType = "application/json",
            examples = @ExampleObject(
                value = "{\"message\": \"Performance metrics reset successfully\", \"timestamp\": \"2024-01-15T10:30:45.123Z\"}"
            )
        )
    )
    public Map<String, Object> reset() {
        performanceMonitor.resetPerformanceSummary();
        return Map.of("message", "Performance metrics reset successfully",
                "timestamp", Instant.now().toString());
    }
}
