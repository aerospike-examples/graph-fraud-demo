package com.example.fraud.fraud;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;
import java.util.List;

public record FraudCheckDetails(
        @Schema(description = "List of flagged device identifiers associated with the transaction", example = "[\"device123\", \"device456\"]")
        List<Object> flaggedDevices,
        
        @Schema(description = "Sender user/account information", example = "{\"id\": \"user123\", \"name\": \"John Doe\"}")
        Object sender,
        
        @Schema(description = "Receiver user/account information", example = "{\"id\": \"user456\", \"name\": \"Jane Smith\"}")
        Object receiver,
        
        @Schema(description = "Number of connected accounts analyzed", example = "15")
        int connectedAccountsChecked,
        
        @Schema(description = "Timestamp when fraud was detected", example = "2024-01-15T10:30:45.123Z")
        Instant detectionTime,
        
        @Schema(description = "Name of the rule that detected the fraud", example = "high-velocity-check")
        String ruleName
) {
}