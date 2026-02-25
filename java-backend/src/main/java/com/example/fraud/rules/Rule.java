package com.example.fraud.rules;

import com.example.fraud.fraud.FraudResult;
import com.example.fraud.fraud.TransactionInfo;
import java.util.List;
import com.fasterxml.jackson.annotation.JsonIgnore;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Getter;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;

@AllArgsConstructor
@Getter
public abstract class Rule {
    @Schema(description = "Unique name identifier for the fraud rule", example = "high-velocity-check")
    private final String name;
    
    @Schema(description = "Detailed description of what the rule detects", example = "Detects high-velocity transactions from a single account")
    private final String description;
    
    @Schema(description = "List of key indicators this rule monitors", example = "[\"transaction_count\", \"time_window\", \"velocity\"]")
    private final List<String> keyIndicators;
    
    @Schema(description = "Common use case for this fraud rule", example = "Prevents account takeover and automated attacks")
    private final String commonUseCase;
    
    @Schema(description = "Computational complexity of the rule", example = "O(n)")
    private final String complexity;
    
    @Schema(description = "Whether the rule is currently active", example = "true")
    private boolean enabled;
    
    @Schema(description = "Whether the rule runs asynchronously", example = "false")
    private final boolean runAsync;
    
    @JsonIgnore
    protected final GraphTraversalSource g;

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public abstract FraudResult executeRule(final TransactionInfo info);
}
