package com.example.fraud.rules;

import com.example.fraud.fraud.FraudOutcome;
import com.example.fraud.fraud.TransactionInfo;
import lombok.AllArgsConstructor;
import lombok.Getter;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;

@AllArgsConstructor
@Getter
public abstract class Rule {
    private final String name;
    private final String complexity;
    private final boolean isEnabled;
    private final boolean shouldRunAsync;
    protected final GraphTraversalSource g;

    public abstract FraudOutcome executeRule(final TransactionInfo info);
}
