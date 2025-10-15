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
    private final String description;
    private final List<String> keyIndicators;
    private final String commonUseCase;
    private final String complexity;
    private final boolean enabled;
    private final boolean runAsync;
    protected final GraphTraversalSource g;

    public abstract FraudOutcome executeRule(final TransactionInfo info);
}
