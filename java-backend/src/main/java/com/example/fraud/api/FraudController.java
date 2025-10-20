package com.example.fraud.api;

import com.example.fraud.fraud.FraudService;

import com.example.fraud.rules.Rule;

import java.util.List;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/fraud")
public class FraudController {

    private final FraudService fraudService;

    public FraudController(FraudService fraudService) {
        this.fraudService = fraudService;
    }

    @GetMapping("/rules")
    public List<Rule> getMaxRate() {
        List<Rule> rules = fraudService.getFraudRulesList();
        return List.copyOf(rules);
    }

    @PostMapping("/fraud-patterns/run")
    public ResponseEntity<?> runFraudPatterns() {
        try {
            return ResponseEntity.ok(Map.of("message", "Fraud patterns analysis started"));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/detect/fraudulent-transactions")
    public ResponseEntity<?> detectFraudulentTransactions() {
        try {
            return ResponseEntity.ok(Map.of("message", "Fraudulent transactions detection completed", "count", 0));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }
}
