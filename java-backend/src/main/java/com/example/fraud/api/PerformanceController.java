package com.example.fraud.api;

import com.example.fraud.monitor.PerformanceMonitor;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.Map;

@RestController
@RequestMapping("/performance")
public class PerformanceController {

    private final PerformanceMonitor performanceMonitor;

    public PerformanceController(PerformanceMonitor performanceMonitor) {
        this.performanceMonitor = performanceMonitor;
    }

    // GET /performance/stats?time_window=
    @GetMapping("/stats")
    public Map<String, Object> stats(@RequestParam(name = "time_window", defaultValue = "5") @Min(1) @Max(60) int minutes) {
        var stats = performanceMonitor.getAllStats(minutes);
        // TODO: Transaction Stats are coming back 0, and all fraud
        return Map.of(
                "performance_stats", stats,
                "time_window_minutes", minutes,
                "timestamp", Instant.now().toString()
        );
    }

    // POST /performance/reset
    @PostMapping("/reset")
    public Map<String, Object> reset() {
        performanceMonitor.resetPerformanceSummary();
        return Map.of("message", "Performance metrics reset successfully",
                "timestamp", Instant.now().toString());
    }
}
