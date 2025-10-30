package com.example.fraud.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum FraudCheckStatus {
    REVIEW("review", 1),
    BLOCKED("blocked", 2),
    CLEARED("cleared", 0);

    private final String value;
    private final int rank;

    public boolean lte(FraudCheckStatus other) { return other != null && this.rank <= other.rank; }

}