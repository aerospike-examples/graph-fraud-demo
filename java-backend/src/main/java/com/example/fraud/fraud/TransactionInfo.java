package com.example.fraud.fraud;

import io.swagger.v3.oas.annotations.media.Schema;

public record TransactionInfo(
        @Schema(description = "Whether the transaction was created successfully", example = "true")
        boolean success,
        
        @Schema(description = "Unique identifier of the transaction edge in the graph", example = "edge123")
        Object edgeId,
        
        @Schema(description = "Unique transaction identifier", example = "txn456")
        Object txnId,
        
        @Schema(description = "Source account identifier", example = "account123")
        Object fromId,
        
        @Schema(description = "Destination account identifier", example = "account456")
        Object toId,
        
        @Schema(description = "Transaction amount", example = "250.75")
        double amount,
        
        @Schema(description = "Performance metrics for transaction creation")
        PerformanceInfo performanceInfo
) {
}
