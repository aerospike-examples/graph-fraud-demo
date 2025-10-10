package com.example.fraud.fraud;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class FraudOutcome {
    private final boolean isFraud;
    private final String reason;
    private final FraudResult result;
}
