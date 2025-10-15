package com.example.fraud.cli;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.generator.GeneratorService;
import com.example.fraud.generator.WarmupService;
import com.example.fraud.graph.GraphService;
import org.springframework.stereotype.Service;

@Service
public class ServiceOrchestrator {
    private final WarmupService warmupService;
    private final GeneratorService generatorService;
    private final GraphService graphService;
    private final FraudService fraudService;

    public ServiceOrchestrator(WarmupService warmupService,
                               GeneratorService generatorService,
                               FraudService fraudService,
                               GraphService graphService) {
        this.warmupService = warmupService;
        this.generatorService = generatorService;
        this.graphService = graphService;
        this.fraudService = fraudService;
        runWarmupFlow();
    }

    public void runWarmupFlow() {
        warmupService.runWithCleanup();
    }

    public void runShutdownFLow() {
        generatorService.shutdown();
        fraudService.shutdown();
        graphService.shutdown();
    }
}