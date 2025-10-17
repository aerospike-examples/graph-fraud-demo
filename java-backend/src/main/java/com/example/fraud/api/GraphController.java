package com.example.fraud.api;

import com.example.fraud.graph.GraphService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Map;

@RestController
@RequestMapping("/")
public class GraphController {

    private final GraphService graph;

    public GraphController(GraphService graph) {
        this.graph = graph;
    }

    // GET /
    @GetMapping
    public Map<String, Object> root() {
        return Map.of("message", "Fraud Detection API is running", "status", "healthy");
    }

    // HEAD /health
    @RequestMapping(path = "/health", method = RequestMethod.HEAD)
    public ResponseEntity<Void> dockerHealth() { return ResponseEntity.ok().build(); }

    // GET /health
    @GetMapping("/health")
    public Map<String, Object> health() {
        String graphStatus = graph.healthCheck() ? "connected" : "error";
        return Map.of("status", "healthy", "graph_connection", graphStatus, "timestamp", Instant.now().toString());
    }

    // GET /dashboard/stats
    @GetMapping("/dashboard/stats")
    public Object dashboardStats() { return graph.getDashboardStats(); }

    // ----- Users -----

    // GET /users
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

    // GET /users/stats
    @GetMapping("/users/stats")
    public Object getUsersStats() { return graph.getUserStats(); }

    // GET /users/{user_id}
    @GetMapping("/users/{user_id}")
    public ResponseEntity<?> getUser(@PathVariable("user_id") String userId) {
        var summary = graph.getUserSummary(userId);
        return (summary == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(summary);
    }

    // ----- Transactions -----

    // GET /transactions
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

    // DELETE /transactions
    @DeleteMapping("/transactions")
    public Object deleteAllTransactions() {
        try {
            graph.dropTransactions();
            return true;
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        }
    }

    // GET /transactions/stats
    @GetMapping("/transactions/stats")
    public Object transactionStats() { return graph.getTransactionStats(); }

    // GET /transactions/flagged
    @GetMapping("/transactions/flagged")
    public Object flaggedTransactions(
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "12") @Min(1) @Max(100) int page_size
    ) {
        return graph.getFlaggedTransactionsPaginated(page, page_size);
    }

    // GET /transaction/{transaction_id}
    @GetMapping("/transaction/{transaction_id}")
    public ResponseEntity<?> getTransactionDetail(@PathVariable("transaction_id") String transactionId) {
        String id = URLDecoder.decode(transactionId, StandardCharsets.UTF_8);
        var detail = graph.getTransactionSummary(id);
        return (detail == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(detail);
    }

    // ----- Accounts -----

    // GET /accounts
    @GetMapping("/accounts")
    public Object getAccounts() { return Map.of("accounts", graph.getAllAccounts()); }

    // GET /accounts/flagged
    @GetMapping("/accounts/flagged")
    public Object getFlaggedAccounts() {
        var flagged = graph.getFlaggedAccounts();
        return Map.of("flagged_accounts", flagged, "count", flagged.size());
    }

    // POST /accounts/{account_id}/flag
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

    // DELETE /accounts/{account_id}/flag
    @DeleteMapping("/accounts/{account_id}/flag")
    public ResponseEntity<?> unflagAccount(@PathVariable("account_id") String accountId) {
        boolean ok = graph.unflagAccount(accountId);
        return ok ? ResponseEntity.ok(Map.of(
                "message", "Account " + accountId + " unflagged successfully",
                "account_id", accountId,
                "timestamp", Instant.now().toString()
        )) : ResponseEntity.notFound().build();
    }

    // ----- Bulk loading & admin -----

    // POST /bulk-load
    @PostMapping("/bulk-load")
    public Object bulkLoadCsv(@RequestParam(required = false) String vertices_path,
                              @RequestParam(required = false) String edges_path) {
        try {
            graph.seedSampleData();
            return true;
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        }
    }

    // GET /bulk-load-status
    @GetMapping("/bulk-load-status")
    public Object bulkLoadStatus() { return graph.getBulkloadStatus(); }

    // GET /admin/indexes
    @GetMapping("/admin/indexes")
    public Object getIndexInfo() { return graph.inspectIndexes(); }

    // POST /admin/indexes/create-transaction-indexes
    @PostMapping("/admin/indexes/create-transaction-indexes")
    public Object createTxnIndexes() { return graph.createFraudDetectionIndexes(); }

    /* simple response wrapper if you need typed DTOs later */
    record ApiMessage(String message) {}
}
