package com.example.fraud.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum MetadataRecord {
    USERS("user"),
    FRAUD("fraud"),
    ACCOUNTS("account");

    private final String value;
}
