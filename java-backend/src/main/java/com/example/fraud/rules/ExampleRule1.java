package com.example.fraud.rules;

import com.example.fraud.fraud.FraudOutcome;
import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.TransactionInfo;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import lombok.experimental.SuperBuilder;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;

@SuperBuilder
public class ExampleRule1 extends Rule {

    @Override
    public FraudOutcome executeRule(final TransactionInfo info) {

        final long startTime = System.nanoTime();
        boolean ok = true;
        try {
            @SuppressWarnings("unchecked")
            final Map<String, Object> connections = g.E(info.getEdgeId())
                    .project("sender", "receiver")
                    .by(__.outV().has("fraud_flag", true).id())
                    .by(__.inV().has("fraud_flag", true).id())
                    .next();

            Object sender = connections.get("sender");
            Object receiver = connections.get("receiver");

            if (sender == null && receiver == null) {
                return perfOkAndPass(perf, startTime, 1);
            }

            List<Map<String, Object>> flagged = new ArrayList<>(2);
            if (sender != null) flagged.add(flaggedConnection(String.valueOf(sender), "sender", 100));
            if (receiver != null) flagged.add(flaggedConnection(String.valueOf(receiver), "receiver", 100));

            int total = flagged.size();
            int score = 100;
            String reason = "Connected to " + total + " flagged account(s) - 'direct fraud'";
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("flagged_connections", flagged);
            details.put("detection_time", Instant.now().toString());
            details.put("fraud_score", score);
            details.put("reason", reason);
            details.put("rule", "RT1_SingleLevelFlaggedAccountRule");

            FraudResult result = new FraudResult(score, "blocked", details);
            return perfOkAndHit(perf, startTime, 1, reason, result);

        } catch (Exception e) {
            ok = false;
            log.error("Error in RT1 fraud detection for txn {}: {}", txnId, e.toString());
            return perfFail(perf, t0, 1, "Detection error: " + e.getMessage());
        } finally {
            if (ok) perf.recordRt1Performance((System.nanoTime() - t0) / 1_000_000.0, true, getComplexity(), false);
            else perf.recordRt1Performance((System.nanoTime() - t0) / 1_000_000.0, false, getComplexity(), false);
        }
    }
}
