package com.example.fraud.api;

import com.example.fraud.generator.GeneratorService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
@Tag(name = "Transaction Generation", description = "Control transaction generation and monitoring")
public class GeneratorController {
    private final GeneratorService transactionGenerator;

    public GeneratorController(GeneratorService transactionGenerator) {
        this.transactionGenerator = transactionGenerator;
    }

    @GetMapping("/generate/status")
    @Operation(summary = "Get Generation Status", description = "Get current transaction generation status and statistics")
    public ResponseEntity<?> status() {
        var status = transactionGenerator.getStatus();
        var total = transactionGenerator.getTotalTransactions();

        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("running", status.running());
        out.put("generationRate", status.generationRate());
        out.put("startTime", status.startTime());
        out.put("total", total);
        return ResponseEntity.ok(out);
    }

    @PostMapping("/generate/start")
    @Operation(summary = "Start Generation", description = "Start transaction generation at specified rate")
    public ResponseEntity<?> start(@RequestBody Map<String, Object> body) {
        try {
            int rate = ((Number) body.get("rate")).intValue();
            int max = transactionGenerator.getMaxTransactionRate();

            if (rate > max) {
                return ResponseEntity.badRequest().body(
                        Map.of("error", "Generation rate " + rate + " exceeds maximum allowed rate of " + max)
                );
            }

            boolean ok = transactionGenerator.startGeneration(rate);
            if (!ok) {
                return ResponseEntity.badRequest().body(
                        Map.of("error", "Transaction generation is already running")
                );
            }

            return ResponseEntity.ok(Map.of(
                    "message", "Transaction generation started at " + rate + " transactions/second",
                    "status", "started",
                    "rate", rate,
                    "max_rate", max
            ));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(
                    Map.of("error", "Failed to start generation: " + e.getMessage())
            );
        }
    }

    @PostMapping("/generate/stop")
    @Operation(summary = "Stop Generation", description = "Stop transaction generation")
    public ResponseEntity<?> stop() {
        boolean ok = transactionGenerator.stopGeneration();
        if (!ok) {
            return ResponseEntity.badRequest().body(
                    Map.of("error", "Transaction generation is not running")
            );
        }
        return ResponseEntity.ok(Map.of(
                "message", "Transaction generation stopped",
                "status", "stopped"
        ));
    }

    @GetMapping("/transaction-generation/max-rate")
    @Operation(summary = "Get Max Rate", description = "Get maximum allowed transaction generation rate")
    public ResponseEntity<?> getMaxRate() {
        int max = transactionGenerator.getMaxTransactionRate();
        return ResponseEntity.ok(Map.of(
                "max_rate", max,
                "message", "Maximum allowed transaction generation rate: " + max + " transactions/second"
        ));
    }
}

