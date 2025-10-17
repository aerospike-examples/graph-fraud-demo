package com.example.fraud.rules;

import com.example.fraud.fraud.FlaggedConnection;
import com.example.fraud.fraud.FraudCheckDetails;
import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.PerformanceInfo;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.model.FraudCheckStatus;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import lombok.experimental.SuperBuilder;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ExampleRule2 extends Rule {

    public ExampleRule2(GraphTraversalSource g,
                        @Value("${rules.example-rule-2.name:Transaction with Users Associated with Flagged Accounts}") String name,
                        @Value("${rules.example-rule-2.description:Threat detection via 2-hop lookup}") String description,
                        @Value("#{'rules.example-rule-2.key-indicators:Transaction directed to users associated with flagged accounts,Multi-hop neighborhood analysis,Real-time risk assessment'.split(',')}") List<String> keyIndicators,
                        @Value("${rules.example-rule-2.common-use-case:Immediate threat detection, known fraudster connections}'") String commonUseCase,
                        @Value("${rules.example-rule-2.complexity:LOW}") String complexity,
                        @Value("${rules.example-rule-2.enabled:true}") boolean enabled,
                        @Value("${rules.example-rule-2.run-async:false}") boolean runAsync
    ) {
        super(name, description, keyIndicators, commonUseCase, complexity, enabled, runAsync, g);
    }

    @Override
    public FraudResult executeRule(final TransactionInfo info) {
        Object edgeId = info.edgeId();

        final Instant t0 = Instant.now();
        try {
            @SuppressWarnings("unchecked") final Map<String, Object> connections = (Map<String, Object>) g.E(edgeId)
                    .project("sender", "receiver")
                    .by(__.outV().bothE("TRANSACTS").bothV().has("fraud_flag", true).id().dedup().fold())
                    .by(__.inV().bothE("TRANSACTS").bothV().has("fraud_flag", true).id().dedup().fold())
                    .next();

            @SuppressWarnings("unchecked") final List<Object> senderList = (List<Object>) connections.get("sender");
            @SuppressWarnings("unchecked") final List<Object> receiverList = (List<Object>) connections.get("receiver");

            if ((senderList == null || senderList.isEmpty()) &&
                    (receiverList == null || receiverList.isEmpty())) {
                return new FraudResult(false, 0, "No flagged entities involved",
                        FraudCheckStatus.CLEARED, null, false,
                        new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));
            }

            final List<Object> flagged = new ArrayList<Object>(
                    (senderList != null ? senderList.size() : 0) + (receiverList != null ? receiverList.size() : 0));

            if (senderList != null) {
                for (Object o : senderList) {
                    flagged.add(o);
                }
            }

            if (receiverList != null) {
                for (Object o : receiverList) {
                    flagged.add(o);
                }
            }

            final int total = flagged.size();
            final int score = Math.min(75 + total * 5, 95);
            final FraudCheckStatus status = (score >= 90) ? FraudCheckStatus.BLOCKED : FraudCheckStatus.REVIEW;
            final String reason = "Connected to " + total + " flagged account(s) - transaction partners";

            final FraudCheckDetails details = new FraudCheckDetails(flagged, senderList, info.toId(),
                    total, Instant.now(), this.getName());
            return new FraudResult(true, score, reason, status, details, false,
                    new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));

        } catch (Exception e) {
            return new FraudResult(false, 0, e.getMessage(),
                    FraudCheckStatus.CLEARED, null, true,
                    new PerformanceInfo(t0, Duration.between(t0, Instant.now()), false));
        }
    }
}
