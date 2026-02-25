package com.example.fraud.generator;

import com.example.fraud.model.TransactionType;
import java.time.Instant;

public record TransactionTask(
        Instant startTime, double amount, TransactionType transactionType
) {
}
