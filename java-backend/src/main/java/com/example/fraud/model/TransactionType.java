package com.example.fraud.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor

public enum TransactionType {
    TRANSFER("transfer"),
    PAYMENT("payment"),
    DEPOSIT("deposit"),
    WITHDRAWAL("withdrawal");

    private final String value;
}
