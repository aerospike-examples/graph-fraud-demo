package com.example.fraud.api;

import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.graph.GraphService;
import com.example.fraud.model.TransactionType;
import com.example.fraud.util.FraudUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
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

    @RequestMapping(path = "/health", method = RequestMethod.HEAD)
    public ResponseEntity<Void> dockerHealth() {
        return ResponseEntity.ok().build();
    }

    @GetMapping("/health")
    @Operation(summary = "Health Check", description = "Check if the service is running and database is connected")
    public Map<String, Object> health() {
        String graphStatus = graph.healthCheck() ? "connected" : "error";
        return Map.of("status", "healthy", "graph_connection", graphStatus, "timestamp", Instant.now().toString());
    }

    @GetMapping("/dashboard/stats")
    @Operation(summary = "Dashboard Statistics", description = "Get overall system statistics for the dashboard")
    public Object dashboardStats() {
        return graph.getDashboardStats();
    }

    @GetMapping("/users")
    public Object getUsers(
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(required = false) @Min(1) @Max(100) Integer page_size,
            @RequestParam(defaultValue = "name") String order_by,
            @RequestParam(defaultValue = "asc") String order,
            @RequestParam(required = false) String query
    ) {
        return graph.search("user", page, page_size, order_by, order, query);
    }

    @GetMapping("/users/stats")
    public Object getUsersStats() {
        return graph.getUserStats();
    }

    @GetMapping("/users/{user_id}")
    public ResponseEntity<?> getUser(@PathVariable("user_id") String userId) {
        var summary = graph.getUserSummary(userId);
        return (summary == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(summary);
    }

    @GetMapping("/transactions")
    public Object getTransactions(
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "12") @Min(1) @Max(100) int page_size,
            @RequestParam(defaultValue = "name") String order_by,
            @RequestParam(defaultValue = "asc") String order,
            @RequestParam(required = false) String query
    ) {
        return graph.search("txns", page, page_size, order_by, order, query);
    }


    @DeleteMapping("/transactions")
    public Object deleteAllTransactions() {
        try {
            graph.dropTransactions();
            return true;
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        }
    }

    @GetMapping("/transactions/stats")
    public Object transactionStats() {
        return graph.getTransactionStats();
    }

    @GetMapping("/transactions/flagged")
    public Object flaggedTransactions(
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "12") @Min(1) @Max(100) int page_size
    ) {
        return graph.getFlaggedTransactionsPaginated(page, page_size);
    }

    @GetMapping("/transaction/{transaction_id}")
    public ResponseEntity<?> getTransactionDetail(@PathVariable("transaction_id") String transactionId) {
        String id = URLDecoder.decode(transactionId, StandardCharsets.UTF_8);
        var detail = graph.getTransactionSummary(id);
        return (detail == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(detail);
    }

    @GetMapping("/accounts")
    public Object getAccounts() {
        return Map.of("accounts", graph.getAllAccounts());
    }

    @GetMapping("/accounts/flagged")
    public Object getFlaggedAccounts() {
        var flagged = graph.getFlaggedAccounts();
        return Map.of("flagged_accounts", flagged, "count", flagged.size());
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

    @DeleteMapping("/accounts/{account_id}/flag")
    public ResponseEntity<?> unflagAccount(@PathVariable("account_id") String accountId) {
        boolean ok = graph.unflagAccount(accountId);
        return ok ? ResponseEntity.ok(Map.of(
                "message", "Account " + accountId + " unflagged successfully",
                "account_id", accountId,
                "timestamp", Instant.now().toString()
        )) : ResponseEntity.notFound().build();
    }

    @GetMapping("/admin/indexes")
    public Object getIndexInfo() {
        return graph.inspectIndexes();
    }

    @PostMapping("/admin/indexes/create-transaction-indexes")
    public Object createTxnIndexes() {
        return graph.createFraudDetectionIndexes();
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
