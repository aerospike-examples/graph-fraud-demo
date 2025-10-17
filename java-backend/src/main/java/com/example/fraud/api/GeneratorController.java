package com.example.fraud.api;

import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.generator.GeneratorService;
import com.example.fraud.graph.GraphService;
import com.example.fraud.model.TransactionType;
import com.example.fraud.util.FraudUtil;

import jakarta.validation.constraints.Min;
import java.time.Instant;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/generator")
public class GeneratorController {
    private final GeneratorService transactionGenerator;

    public GeneratorController(GeneratorService transactionGenerator) {
        this.transactionGenerator = transactionGenerator;
    }

    // POST /generator/generate  -> 204 No Content
    @PostMapping("/generate")
    public ResponseEntity<?> generateRandomTransaction() {
        TransactionInfo t = transactionGenerator.generateTransaction();
        if (!t.success()) {
            return ResponseEntity.badRequest().body(
                    new ApiMessage("Generate random transaction request failed")
            );
        }
        return ResponseEntity.noContent().build();
    }

    // POST /generator/start?rate=
    @PostMapping("/start")
    public ResponseEntity<?> start(
            @RequestParam @Min(1) int rate,
            @RequestParam(defaultValue = "") String start
    ) {
        int max = transactionGenerator.getMaxTransactionRate();
        if (rate > max) {
            return ResponseEntity.badRequest().body(
                    new ApiMessage("Generation rate " + rate + " exceeds maximum allowed rate of " + max)
            );
        }
        boolean ok = transactionGenerator.startGeneration(rate);
        if (!ok) {
            return ResponseEntity.badRequest().body(new ApiMessage("Transaction generation is already running"));
        }
        return ResponseEntity.ok(new StartResponse(
                "Transaction generation started at " + rate + " transactions/second", "started", rate, max));
    }

    // POST /generator/stop
    @PostMapping("/stop")
    public ResponseEntity<?> stop() {
        boolean ok = transactionGenerator.stopGeneration();
        if (!ok) {
            return ResponseEntity.badRequest().body(new ApiMessage("Transaction generation is not running"));
        }
        return ResponseEntity.ok(new ApiStatus("Transaction generation stopped", "stopped"));
    }

    // GET /generator/max-rate
    @GetMapping("/max-rate")
    public ResponseEntity<?> getMaxRate() {
        int max = transactionGenerator.getMaxTransactionRate();
        return ResponseEntity.ok(new MaxRateResponse(max,
                "Maximum allowed transaction generation rate: " + max + " transactions/second"));
    }


    // GET /generator/status
    @GetMapping("/status")
    public ResponseEntity<?> status() {
        int totalTransactions = transactionGenerator.getTotalTransactions();
        return ResponseEntity.ok(transactionGenerator.getStatus());
    }

    record ApiMessage(String message) {
    }

    record ApiStatus(String message, String status) {
    }

    record StartResponse(String message, String status, int rate, int max_rate) {
    }

    record MaxRateResponse(int max_rate, String message) {
    }
}
