package com.example.fraud.fraud;

import java.time.Instant;
import java.util.List;

public record FraudCheckDetails(List<Object> flaggedDevices, Object sender, Object receiver,
                                int connectedAccountsChecked, Instant detectionTime, String ruleName) {
}