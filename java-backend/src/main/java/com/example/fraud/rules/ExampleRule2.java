package com.example.fraud.rules;

import com.example.fraud.fraud.FraudOutcome;
import com.example.fraud.fraud.TransactionInfo;
import lombok.experimental.SuperBuilder;

@SuperBuilder
public class ExampleRule2 extends Rule {

    @Override
    public FraudOutcome executeRule(final TransactionInfo info) {
        return null;
    }
}
