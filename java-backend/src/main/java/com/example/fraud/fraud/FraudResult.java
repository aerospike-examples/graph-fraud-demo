package com.example.fraud.fraud;

import com.example.fraud.model.FraudCheckStatus;

public record FraudResult
        (boolean isFraud,
         int fraudScore,
         String reason,
         FraudCheckStatus status,
         FraudCheckDetails details,
         boolean exceptionOccurred,
         PerformanceInfo performanceInfo) {
}

