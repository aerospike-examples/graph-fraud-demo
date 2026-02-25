package com.example.fraud.fraud;

import com.example.fraud.model.FraudCheckStatus;
import io.swagger.v3.oas.annotations.media.Schema;

public record FraudResult(
        @Schema(description = "Whether fraud was detected", example = "true")
        boolean isFraud,
        
        @Schema(description = "Fraud risk score (0-100)", example = "85")
        int fraudScore,
        
        @Schema(description = "Reason for the fraud determination", example = "High velocity transactions detected")
        String reason,
        
        @Schema(description = "Status of the fraud check (CLEARED, REVIEW, BLOCKED)", example = "REVIEW")
        FraudCheckStatus status,
        
        @Schema(description = "Detailed information about the fraud check")
        FraudCheckDetails details,
        
        @Schema(description = "Whether an exception occurred during checking", example = "false")
        boolean exceptionOccurred,
        
        @Schema(description = "Performance metrics for fraud check execution")
        PerformanceInfo performanceInfo
) {
}

