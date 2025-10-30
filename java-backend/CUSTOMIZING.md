# Customizing the Java Backend

This guide explains how to extend the backend for your own use cases: adding new rules, wiring them into the fraud service, configuring properties, and validating performance.

Architecture at a glance

- Transactions are created in `GeneratorService`, persisted via `GraphService.createTransaction(...)`.
- `FraudService.submitFraudDetection(...)` executes all enabled `Rule`s for each transaction and persists consolidated outcomes.
- `PerformanceMonitor` records transaction and per-rule performance for the Admin Performance UI.
- Configuration is bound via Spring `@ConfigurationProperties` (e.g., `graph.*`, `generation.*`, `fraud.*`) and per-rule `@Value` properties.

# Custom Rules
Configuring rules
Since this application uses Spring Boot, classes annotated with `@Service` or `@Component` can have properties and other services injected via constructors. Rules follow the same pattern: tag each rule with `@Component` and Spring will inject it into the fraud service automatically.

Adding a new rule

1. Create a class in `src/main/java/com/example/fraud/rules/` that extends `Rule`:

```java
package com.example.fraud.rules;

import com.example.fraud.fraud.FraudCheckDetails;
import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.PerformanceInfo;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.model.FraudCheckStatus;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ExampleRuleX extends Rule {
  public ExampleRuleX(GraphTraversalSource g,
                      @Value("${rules.example-rule-x.name:My Rule}") String name,
                      @Value("${rules.example-rule-x.description:Detects my pattern}") String description,
                      @Value("#{'Key indicator A,Key indicator B'.split(',')}") List<String> keyIndicators,
                      @Value("${rules.example-rule-x.common-use-case:My use case}") String commonUseCase,
                      @Value("${rules.example-rule-x.complexity:LOW}") String complexity,
                      @Value("${rules.example-rule-x.enabled:true}") boolean enabled,
                      @Value("${rules.example-rule-x.run-async:false}") boolean runAsync) {
    super(name, description, keyIndicators, commonUseCase, complexity, enabled, runAsync, g);
  }

  @Override
  public FraudResult executeRule(final TransactionInfo info) {
    final Instant t0 = Instant.now();
    try {
      // Use `g` to traverse around the transaction: info.fromId(), info.toId(), info.edgeId()
      boolean isFraud = false; // set by traversal logic

      if (!isFraud) {
        // Return details with ruleName even when cleared so metrics remain complete
        return new FraudResult(false, 0, "No findings",
            FraudCheckStatus.CLEARED,
            new FraudCheckDetails(List.of(), info.fromId(), info.toId(), 0, Instant.now(), this.getName()),
            false,
            new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));
      }

      int score = 80;
      String reason = "Detected my pattern";
      FraudCheckStatus status = (score >= 90) ? FraudCheckStatus.BLOCKED : FraudCheckStatus.REVIEW;
      FraudCheckDetails details = new FraudCheckDetails(List.of(), info.fromId(), info.toId(), 0, Instant.now(), this.getName());
      return new FraudResult(true, score, reason, status, details, false,
          new PerformanceInfo(t0, Duration.between(t0, Instant.now()), true));
    } catch (Exception e) {
      return new FraudResult(false, 0, e.getMessage(),
          FraudCheckStatus.CLEARED, null, true,
          new PerformanceInfo(t0, Duration.between(t0, Instant.now()), false));
    }
  }
}
```

Why include details on “no fraud”?

- The performance UI aggregates metrics by rule name. Returning a non-null `FraudCheckDetails` with the rule name 
- on clear results ensures the metrics remain stable, even if most traffic is clean.

Expose per-rule configuration
Add properties to `application.properties` (or env vars):

```properties
rules.example-rule-x.name=My Rule
rules.example-rule-x.description=Detects my pattern
rules.example-rule-x.enabled=true
rules.example-rule-x.run-async=false
```

Enable/disable rules at runtime

- `GET /api/fraud/rules` lists all rules.
- `POST /api/fraud/rules/toggle {"name":"My Rule","enabled":true}` toggles enabled state. The Admin UI “Real Time Fraud Scenarios” uses these.

Persisting outcomes

- `FraudService` writes `is_fraud`, `fraud_score`, `fraud_status`, `eval_timestamp`, and `details` onto the transaction edge for UI consumption. Prefer concise, structured details.

Performance tips for rule traversals

- Ensure indexes exist on properties used in `has(...)`, `order().by(...)`, and joins.
- Minimize fan-out; dedup early; fetch only necessary properties.
- Benchmark each rule individually with representative data.

Global tuning knobs

- Client (backend):
  - `graph.main-connection-pool-size`, `graph.fraud-connection-pool-size`
  - `fraud.fraud-worker-pool-size`
- AGS (server):
  - Gremlin pools, per-connection request limits, and JVM heap/GC (see docs/setup.md)

Testing end-to-end

1. Seed a small dataset that triggers your rule.
2. Submit transactions; verify the transaction detail page and Admin Performance reflect your rule.
3. Increase load; ensure p95 latency remains acceptable.

# Metadata
The metadata is handled by the `AerospikeMetadataManager` singleton, which stores records of metadata directly
in the Aerospike Database, in its own set, as opposed to through AGS.

## AerospikeMetadataManager
This singleton is used to increment, and write data from the `AerospikeMetadata` instances.
When you find where you want to increment your data, inject `AerospikeMetadataManager` into its constructor (and as
a final variable), and call 
`metadataManager.incrementCount(MetadataRecord.MYENUM, <bin-name>, amountToIncrement);`

When you want to read one of the metadatas, simply call 
`metadataManager.readRecord(MetadataRecord.<TYPE>);`
And it will return the Aerospike record specified as a `Map<String, Object>`, where you can extract each value.
a
## Creating Custom Metadata Records
Adding a new metadata record is just as easy as adding a new rule, and follows very similar semantics.

First start by creating a class that extends `AerospikeMetadata`, and tag it as a springboot component with
`@Component("<metadata-name>")`.
The `<metadata-name>` will be how your metadata is referred to in the application.
Now in the `model/MetadataRecord` enum, create a value for your new metadata, this is how your metadata will be
accessed by all services in the application.

This class only needs a single constructor, and in this constructor there are two focuses: `binDefaults` and 
`binToCount`.
Currently, metadata is only used with Longs, so `binToCount` is a `Map<String, LongAdder>`, and `binDefaults` is
a `Map<String, Long` with the key to both being the name of the bin.

Set `binDefaults` to the default on first load, and `binToCount` to a `LongAdder`.

Now your metadata is ready to go! It will be picked up automatically by springboot, and added into the
`AerospikeMetadataManager` class.

It should now look something like this:
```java 
@Component("example")
public class ExampleMetadata extends AerospikeMetadata {

    protected NameMetadata(@Value("${metadata.exampleMetadataName:example}") String metadataName) {
        super(metadataName);
        // Lets say you want to set a default based on something in your app
        long parameter = 20000L;
        // Set the adders for incrementation
        binToCount.put("exampleMetadata", new LongAdder());
        binToCount.put("exampleMetadata2", new LongAdder());
        
        // Set the defaults for loading when there is no record
        Long defaultExampleMetadata = (long) (parameter * .2495);
        Long defaultExampleMetadata2 = (long) (parameter * .1);
        binDefaults.put("exampleMetadata", defaultExampleMetadata);
        binDefaults.put("exampleMetadata2", defaultExampleMetadata2);

    }
}
```
