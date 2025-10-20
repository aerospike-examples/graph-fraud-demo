package com.example.fraud.api;

import com.example.fraud.generator.GeneratorService;
import jakarta.validation.constraints.Min;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RequestMapping("/api")
@RestController
public class GeneratorController {
    private final GeneratorService transactionGenerator;

    public GeneratorController(GeneratorService transactionGenerator) {
        this.transactionGenerator = transactionGenerator;
    }

    @GetMapping("/generate/status")
    public ResponseEntity<?> status() {
        return ResponseEntity.ok(transactionGenerator.getStatus());
    }

    @PostMapping("/generate/start")
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
    public ResponseEntity<?> getMaxRate() {
        int max = transactionGenerator.getMaxTransactionRate();
        return ResponseEntity.ok(Map.of(
                "max_rate", max,
                "message", "Maximum allowed transaction generation rate: " + max + " transactions/second"
        ));
    }
}

