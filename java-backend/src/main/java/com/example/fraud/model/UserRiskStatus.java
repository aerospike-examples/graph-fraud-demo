package com.example.fraud.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor

public enum UserRiskStatus {
    LOW("low", 25),
    MEDIUM("medium", 70),
    HIGH("high", 100);

    private final String value;
    private final int fraudScore;

    public static UserRiskStatus evaluateRiskScore(double score) {
        if (score < LOW.fraudScore) {
            return LOW;
        } else if (score <= MEDIUM.fraudScore) {
            return MEDIUM;
        } else {
            return HIGH;
        }
    }
}
