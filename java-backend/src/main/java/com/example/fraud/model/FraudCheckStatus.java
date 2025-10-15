package com.example.fraud.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum FraudCheckStatus {
    REVIEW("review"),
    BLOCKED("blocked"),
    CLEARED("cleared");

    private final String value;
}