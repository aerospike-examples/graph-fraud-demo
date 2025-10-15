package com.example.fraud.fraud;

public record TransactionInfo
        (boolean success,
         Object edgeId,
         Object txnId,
         Object fromId,
         Object toId,
         double amount,
         PerformanceInfo performanceInfo) {
}
