package com.example.fraud.fraud;


import java.util.List;

// TODO: Rename TransactionSummary, should also take in TransactionInfo.
public record TransactionSummary(List<FraudResult> fraudOutcomes, TransactionInfo transactionInfo) {
}