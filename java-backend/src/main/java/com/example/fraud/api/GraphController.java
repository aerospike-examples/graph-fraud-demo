package com.example.fraud.api;

import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.fraud.TransactionSummary;
import com.example.fraud.fraud.RecentTransactions;
import com.example.fraud.graph.GraphService;
import com.example.fraud.model.TransactionType;
import com.example.fraud.util.FraudUtil;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Min;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@Tag(name = "Graph Operations", description = "Graph database operations and data management")
public class GraphController {

    private final GraphService graph;
    private final RecentTransactions recent;

    public GraphController(GraphService graph, RecentTransactions recent) {
        this.graph = graph;
        this.recent = recent;
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
    @Operation(summary = "Dashboard Statistics", description = "Get overall system statistics for the dashboard")
    public Object dashboardStats() {
        return graph.getDashboardStats();
    }

    @GetMapping("/users/stats")
    public Object getUsersStats() {
        return graph.getUserStats();
    }

    @GetMapping("/users/count")
    public Map<String, Object> getUsersCount() {
        return Map.of("count", graph.getUserCount());
    }

    @PostMapping("/users/summary")
    public Object getUsersSummary(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "User IDs to retrieve summaries for",
                    required = true,
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(
                                    name = "Get User Summaries",
                                    value = "{\"ids\": [\"user1\", \"user2\", \"user3\"]}",
                                    description = "Array of user IDs"
                            )
                    )
            )
            @RequestBody Map<String, List<String>> body) {
        List<String> ids = body == null ? List.of() : body.getOrDefault("ids", List.of());
        return graph.getUsersSummary(ids);
    }

    @GetMapping("/users/{user_id}")
    public ResponseEntity<?> getUser(
            @Parameter(description = "Unique identifier of the user", example = "user123")
            @PathVariable("user_id") String userId) {
        var summary = graph.getUserSummary(userId);
        return (summary == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(summary);
    }

    @DeleteMapping("/data")
    public void clearDB() {
            graph.dropAll();
    }

    @GetMapping("/transactions/stats")
    public Object transactionStats() {
        return graph.getTransactionStats();
    }

    @GetMapping("/accounts/{account_id}")
    public Map<String, Object> accountExists(
            @Parameter(description = "Unique identifier of the account", example = "account456")
            @PathVariable("account_id") String accountId) {
        boolean exists = graph.accountExists(accountId);
        return Map.of("exists", exists, "id", accountId);
    }

    @GetMapping("/accounts/count")
    public Map<String, Object> getAccountsCount() {
        return Map.of("count", graph.getAccountCount());
    }

    @GetMapping("/transaction/{transaction_id}")
    @ApiResponses(value = {
        @ApiResponse(
            responseCode = "200",
            description = "Transaction found with fraud check results",
            content = @Content(
                mediaType = "application/json",
                schema = @Schema(implementation = TransactionSummary.class)
            )
        ),
        @ApiResponse(
            responseCode = "404",
            description = "Transaction not found"
        )
    })
    public ResponseEntity<?> getTransactionDetail(
            @Parameter(description = "Base64 URL-encoded transaction identifier", example = "dHJhbnNhY3Rpb24xMjM=")
            @PathVariable("transaction_id") String transactionId) {
        // Transaction IDs come in base64 encoded since they have / and +
        String onceDecoded = java.net.URLDecoder.decode(transactionId, java.nio.charset.StandardCharsets.UTF_8);
        byte[] bytes = java.util.Base64.getUrlDecoder().decode(onceDecoded);
        String id = new String(bytes, java.nio.charset.StandardCharsets.UTF_8);
        var detail = graph.getTransactionSummary(id);
        return (detail == null) ? ResponseEntity.notFound().build() : ResponseEntity.ok(detail);
    }

    @GetMapping("/transactions/recent")
    @ApiResponse(
        responseCode = "200",
        description = "Successfully retrieved recent transactions with fraud check results",
        content = @Content(
            mediaType = "application/json",
            schema = @Schema(implementation = TransactionSummary.class)
        )
    )
    public Object recentTransactions(
            @Parameter(description = "Maximum number of transactions to return (1-100)", example = "50")
            @RequestParam(name = "limit", defaultValue = "100") int limit,
            @Parameter(description = "Number of transactions to skip for pagination", example = "0")
            @RequestParam(name = "offset", defaultValue = "0") int offset) {
        int capped = Math.min(Math.max(1, limit), 100);
        var ids = recent.page(offset, capped);
        var rows = graph.getTransactionsSummaryByIds(ids);
        return Map.of(
                "total", recent.size(),
                "results", rows
        );
    }

    @PostMapping("/accounts/{account_id}/flag")
    public ResponseEntity<?> flagAccount(
            @Parameter(description = "Unique identifier of the account to flag", example = "account456")
            @PathVariable("account_id") String accountId,
            @Parameter(description = "Reason for flagging the account", example = "Suspicious activity detected")
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
        return Boolean.TRUE;
    }

    @PostMapping("/bulk-load/local")
    public Object bulkLoadCsvLocal() {
        graph.seedLocalData();
        return Boolean.TRUE;
    }

    @DeleteMapping("/accounts/{account_id}/flag")
    public ResponseEntity<?> unflagAccount(
            @Parameter(description = "Unique identifier of the account to unflag", example = "account456")
            @PathVariable("account_id") String accountId) {
        boolean ok = graph.unflagAccount(accountId);
        return ok ? ResponseEntity.ok(Map.of(
                "message", "Account " + accountId + " unflagged successfully",
                "account_id", accountId,
                "timestamp", Instant.now().toString()
        )) : ResponseEntity.notFound().build();
    }

    @PostMapping("/transaction-generation/manual")
    @ApiResponses(value = {
        @ApiResponse(
            responseCode = "200",
            description = "Transaction created successfully",
            content = @Content(
                mediaType = "application/json",
                schema = @Schema(implementation = TransactionInfo.class)
            )
        ),
        @ApiResponse(
            responseCode = "400",
            description = "Invalid transaction parameters",
            content = @Content(
                mediaType = "application/json",
                examples = @ExampleObject(
                    value = "{\"message\": \"Invalid transaction type: invalid\"}"
                )
            )
        )
    })
    public ResponseEntity<?> createManualTransaction(
            @Parameter(description = "Source account ID for the transaction", example = "account123", required = true)
            @RequestParam String from_account_id,
            @Parameter(description = "Destination account ID for the transaction", example = "account456", required = true)
            @RequestParam String to_account_id,
            @Parameter(description = "Transaction amount (minimum: 1)", example = "100.50", required = true)
            @RequestParam @Min(1) double amount,
            @Parameter(description = "Type of transaction (transfer, payment, deposit, withdrawal)", example = "transfer")
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
