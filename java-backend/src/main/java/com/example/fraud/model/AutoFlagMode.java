package com.example.fraud.model;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum AutoFlagMode {
    BOTH("both"),
    SENDER("sender"),
    RECEIVER("receiver");

    private final String value;
}