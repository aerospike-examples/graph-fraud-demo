package com.example.fraud.rules;

import com.example.fraud.fraud.FraudCheckDetails;
import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.PerformanceInfo;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.model.FraudCheckStatus;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ExampleRule3 extends Rule {

    public ExampleRule3(GraphTraversalSource g,
                        @Value("${rules.example-rule-3.name:Transactions with Users Associated with Flagged Devices}") String name,
                        @Value("${rules.example-rule-3.description:Detect threats through flagged device usage}") String description,
                        @Value("#{'Transactions directed to users associated with fradulent devices,Multi-hop neighborhood analysis,Transaction history analysis'.split(',')}") List<String> keyIndicators,
                        @Value("${rules.example-rule-3.common-use-case:Immediate threat detection, known fraudster connections}") String commonUseCase,
                        @Value("${rules.example-rule-3.complexity:HIGH}") String complexity,
                        @Value("${rules.example-rule-3.enabled:true}") boolean enabled,
                        @Value("${rules.example-rule-3.run-async:false}") boolean runAsync
    ) {
        super(name, description, keyIndicators, commonUseCase, complexity, enabled, runAsync, g);
    }

    @Override
    public FraudResult executeRule(final TransactionInfo info) {
        final Instant t0 = Instant.now();
        try {
            final Map<String, Object> results = (Map<String, Object>) g.E(info.edgeId())
                    .project("sender", "receiver", "accounts", "devices")
                    .by(__.outV().in("OWNS").id())
                    .by(__.inV().in("OWNS").id())
                    .by(__.bothV().in("OWNS").out("OWNS").both("TRANSACTS").in("OWNS").id().dedup().fold())
                    .by(__.bothV().in("OWNS").out("OWNS").both("TRANSACTS").in("OWNS").out("USES")
                            .has("fraud_flag", true).id().dedup().fold())
                    .next();

            final List<Object> accounts = (List<Object>)(results.get("accounts"));
            final List<Object> devices = (List<Object>)(results.get("devices"));

            if (devices == null || devices.isEmpty()) {
                return new FraudResult(false, 0, "No flagged entities involved",
                        FraudCheckStatus.CLEARED, null, false,
                        new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));
            }

            int score = 85;
            final String reason = "Transaction involves accounts connected to flagged devices in transaction network";
            final FraudCheckDetails details = new FraudCheckDetails(devices, info.fromId(), info.toId(),
                    (accounts != null ? accounts.size() : 0), Instant.now(), this.getName());

            return new FraudResult(true, score, reason,
                    FraudCheckStatus.REVIEW, details, false,
                    new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));
        } catch (Exception e) {
            return new FraudResult(true, 0, e.getMessage(),
                    FraudCheckStatus.CLEARED, null, true,
                    new PerformanceInfo(t0, Duration.between(t0, Instant.now()), false));
        }
    }
}
