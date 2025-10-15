package com.example.fraud.rules;

import com.example.fraud.fraud.FraudOutcome;
import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.TransactionInfo;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import lombok.experimental.SuperBuilder;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;

@Component
public class ExampleRule1 extends Rule {
    public ExampleRule1(GraphTraversalSource g,
                        @Value("${rules.example-rule-1.name:Transaction to Flagged Account}") String name,
                        @Value("${rules.example-rule-1.description:Detects rapid repeat txns}") String description,
                        @Value("#{'${rules.example-rule-1.key-indicators:velocity,burst}'.split(',')}") List<String> keyIndicators,
                        @Value("${rules.example-rule-1.common-use-case:Card testing}") String commonUseCase,
                        @Value("${rules.example-rule-1.complexity:LOW}") String complexity,
                        @Value("${rules.example-rule-1.enabled:true}") boolean enabled,
                        @Value("${rules.example-rule-1.run-async:false}") boolean runAsync) {
        super(name, description, keyIndicators, commonUseCase, complexity, enabled, runAsync, g);
    }

    @Override
    public FraudOutcome executeRule(final TransactionInfo info) {

        final Instant t0 = Instant.now();
        try {
            @SuppressWarnings("unchecked")
            final Map<String, Object> connections = g.E(info.getEdgeId())
                    .project("sender", "receiver")
                    .by(__.outV().has("fraud_flag", true).id())
                    .by(__.inV().has("fraud_flag", true).id())
                    .next();

            final Boolean senderIsFraud = idToFraudFlag.get(info.fromId());
            final Boolean receiverIsFraud = idToFraudFlag.get(info.toId());

            if (senderIsFraud == null || receiverIsFraud == null) {
                final String errorInfo;
                if (senderIsFraud == null && receiverIsFraud == null) {
                    errorInfo = String.format("Both sender (%s) and receiver (%s) are missing.", info.fromId(), info.toId());
                } else if (senderIsFraud == null) {
                    errorInfo = String.format("Only sender (%s) is missing.", info.fromId());
                } else {
                    errorInfo = String.format("Only receiver (%s) is missing.", info.toId());
                }
                throw new RuntimeException(String.format(
                        "Error, %s expected both sender and receiver to exist in database. %s", getName(), errorInfo));
            }

            if (!senderIsFraud && !receiverIsFraud){
                return new FraudResult(false, 0, "No flagged accounts found",
                        FraudCheckStatus.CLEARED,null, false,
                        new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));
            }


            int score = 0;
            int total = 0;
            final List<Object> flaggedConnections = new ArrayList<Object>();
            if (senderIsFraud) {
                score = 100;
                total++;
                flaggedConnections.add(info.fromId());
            }
            if (receiverIsFraud) {
                score = 100;
                total++;
                flaggedConnections.add(new FlaggedConnection((String) info.fromId(), "receiver", 100));
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
