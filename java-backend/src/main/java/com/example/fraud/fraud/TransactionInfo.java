package com.example.fraud.fraud;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class TransactionInfo {
    private final boolean success;
    private final Object edgeId;
    private final Object txnId;
    private final Object fromId;
    private final Object toId;
    private final double amount;
}
