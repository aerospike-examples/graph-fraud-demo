package com.example.fraud.fraud;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

public record TransactionSummary(
        @Schema(description = "List of fraud check results from all executed rules")
        List<FraudResult> fraudOutcomes,
        
        @Schema(description = "Transaction creation information and metadata")
        TransactionInfo transactionInfo
) {
}