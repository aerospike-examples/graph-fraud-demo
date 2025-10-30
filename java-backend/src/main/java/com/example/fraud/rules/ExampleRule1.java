package com.example.fraud.rules;

import com.example.fraud.fraud.FraudCheckDetails;
import com.example.fraud.fraud.PerformanceInfo;
import com.example.fraud.model.FraudCheckStatus;
import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.TransactionInfo;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.structure.Vertex;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;


@Component
public class ExampleRule1 extends Rule {
    public ExampleRule1(@Qualifier("fraudG") GraphTraversalSource g,
                        @Value("${rules.example-rule-1.name:Transaction to Flagged Account}") String name,
                        @Value("${rules.example-rule-1.description:Immediate threat detection via 1-hop lookup}") String description,
                        @Value("#{'Transaction directed to known flagged account,1-hop graph lookup for immediate detection,Real-time risk assessment'.split(',')}") List<String> keyIndicators,
                        @Value("${rules.example-rule-1.common-use-case:Immediate threat detection, known fraudster connections}") String commonUseCase,
                        @Value("${rules.example-rule-1.complexity:LOW}") String complexity,
                        @Value("${rules.example-rule-1.enabled:true}") boolean enabled,
                        @Value("${rules.example-rule-1.run-async:false}") boolean runAsync) {
        super(name, description, keyIndicators, commonUseCase, complexity, enabled, runAsync, g);
    }

    @Override
    public FraudResult executeRule(final TransactionInfo info) {

        final Instant t0 = Instant.now();
        try {
            final var fraudVertices =
                    g.V(info.toId(), info.fromId()).has("fraud_flag", true).toList();

            if (fraudVertices.isEmpty()) {
                return new FraudResult(false, 0, "No flagged accounts found",
                        FraudCheckStatus.CLEARED,
                        new FraudCheckDetails(List.of(), info.fromId(), info.toId(), 0,
                                Instant.now(), this.getName()),
                        false,
                        new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));
            }

            int score = 0;
            int total = 0;
            final List<Object> flaggedConnections = new ArrayList<Object>();
            for (Vertex v : fraudVertices) {
                score = 100;
                total++;
                flaggedConnections.add(v.id());
            }

            final String reason = "Connected to " + total + " flagged account(s) - 'direct fraud'";
            final FraudCheckDetails details = new FraudCheckDetails(flaggedConnections, info.fromId(), info.toId(),
                    2, Instant.now(), this.getName());

            final FraudCheckStatus status = FraudCheckStatus.BLOCKED;
            return new FraudResult(true, score, reason,
                    status, details, false,
                    new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));

        } catch (Exception e) {
            return new FraudResult(false, 0, e.getMessage(), FraudCheckStatus.CLEARED,
                    null, true,
                    new PerformanceInfo(t0, Duration.between(t0, Instant.now()), false));
        }
    }
}
