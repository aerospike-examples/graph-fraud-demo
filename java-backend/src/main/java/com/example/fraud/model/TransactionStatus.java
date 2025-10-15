package com.example.fraud.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum TransactionStatus {
    PENDING("pending"),
    COMPLETED("completed"),
    FAILED("failed"),
    SUSPICIOUS("suspicious"),
    SAFE("safe"),
    REVIEWED("reviewed"),;

    private final String value;
}
