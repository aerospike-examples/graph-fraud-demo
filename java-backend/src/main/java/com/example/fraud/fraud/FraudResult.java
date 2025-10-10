package com.example.fraud.fraud;

import java.time.Instant;
import java.util.Map;

import lombok.Getter;

@Getter
public class FraudResult {
    private final boolean is_fraud;
    private final int fraud_score;
    private final String status;
    private final Instant timestamp;
    private final Map<String, Object> details;


    public FraudResult(final int score, final String status, final Map<String, Object> details) {
        this.is_fraud = true;
        this.fraud_score = score;
        this.status = status;
        this.details = details;
        this.timestamp = Instant.now();
    }

}
