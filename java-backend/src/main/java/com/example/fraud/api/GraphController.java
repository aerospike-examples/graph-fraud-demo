package com.example.fraud.api;

import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.graph.GraphService;
import com.example.fraud.model.TransactionType;
import com.example.fraud.util.FraudUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Min;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;


import java.time.Instant;
import java.util.Map;

@RestController
@RequestMapping("/api")
@Tag(name = "Graph Operations", description = "Graph database operations and data management")
public class GraphController {

    private final GraphService graph;

    public GraphController(GraphService graph) {
        this.graph = graph;
    }

    @GetMapping("/status")
    @Operation(summary = "API Status", description = "Get API status and basic information")
    public Map<String, Object> root() {
        return Map.of("message", "Fraud Detection API is running", "status", "healthy");
    }

    @GetMapping("/health")
    @Operation(summary = "Health Check", description = "Check if the service is running and database is connected")
    public Map<String, Object> health() {
        String graphStatus = graph.healthCheck() ? "connected" : "error";
        return Map.of("status", "healthy", "graph_connection", graphStatus, "timestamp", Instant.now().toString());
    }

    @GetMapping("/dashboard/stats")
    //TODO: Set this up to new meta data, will be done in graphservice function no change here
    @Operation(summary = "Dashboard Statistics", description = "Get overall system statistics for the dashboard")
    public Object dashboardStats() {
        return graph.getDashboardStats();
    }

    @GetMapping("/users/stats")
    public Object getUsersStats() {
        //TODO: Set this up to new meta data, will be done in graphservice function no change here
        return graph.getUserStats();
    }

    @GetMapping("/users/{user_id}")
    public ResponseEntity<?> getUser(@PathVariable("user_id") String userId) {
        var summary = graph.getUserSummary(userId);
        return (summary == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(summary);
    }


    @DeleteMapping("/transactions")
    public Object deleteAllTransactions() {
            graph.dropAll();
            return true;
    }

    @GetMapping("/transactions/stats")
    public Object transactionStats() {
        return graph.getTransactionStats();
    }

    @GetMapping("/accounts/{account_id}")
    public Map<String, Object> accountExists(@PathVariable("account_id") String accountId) {
        boolean exists = graph.accountExists(accountId);
        return Map.of("exists", exists, "id", accountId);
    }

    @GetMapping("/transaction/{transaction_id}")
    public ResponseEntity<?> getTransactionDetail(@PathVariable("transaction_id") String transactionId) {
        // Do not form-decode here; Spring already decodes percent-encoded path
        // Using URLDecoder would turn '+' into space erroneously for path segments
        var detail = graph.getTransactionSummary(transactionId);
        return (detail == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(detail);
    }

    @PostMapping("/accounts/{account_id}/flag")
    public ResponseEntity<?> flagAccount(@PathVariable("account_id") String accountId,
                                         @RequestParam(defaultValue = "Manual flag for testing") String reason) {
        boolean ok = graph.flagAccount(accountId, reason);
        return ok ? ResponseEntity.ok(Map.of(
                "message", "Account " + accountId + " flagged successfully",
                "account_id", accountId,
                "reason", reason,
                "timestamp", Instant.now().toString()
        )) : ResponseEntity.notFound().build();
    }


    @PostMapping("/bulk-load")
    public Object bulkLoadCsv() {
        graph.seedSampleData();
        return true;
    }

    @DeleteMapping("/accounts/{account_id}/flag")
    public ResponseEntity<?> unflagAccount(@PathVariable("account_id") String accountId) {
        boolean ok = graph.unflagAccount(accountId);
        return ok ? ResponseEntity.ok(Map.of(
                "message", "Account " + accountId + " unflagged successfully",
                "account_id", accountId,
                "timestamp", Instant.now().toString()
        )) : ResponseEntity.notFound().build();
    }

    @PostMapping("/transaction-generation/manual")
    public ResponseEntity<?> createManualTransaction(
            @RequestParam String from_account_id,
            @RequestParam String to_account_id,
            @RequestParam @Min(1) double amount,
            @RequestParam(defaultValue = "transfer") String transaction_type
    ) {
        try {
            TransactionType transactionType = TransactionType.valueOf(transaction_type.toUpperCase());
            String location = FraudUtil.getRandomLocation();
            TransactionInfo result = graph.createManualTransaction(
                    from_account_id, to_account_id, amount, transactionType, "MANUAL", location, Instant.now());
            if (!result.success()) {
                return ResponseEntity.badRequest().body(
                        Map.of("message", "Failed to create transaction")
                );
            }
            return ResponseEntity.ok(Map.of("message", "Transaction created successfully"));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(
                    Map.of("message", "Invalid transaction type: " + transaction_type)
            );
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(
                    Map.of("message", "Failed to create transaction: " + e.getMessage())
            );
        }
    }
}
