package com.example.fraud.cli;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.generator.GeneratorService;
import com.example.fraud.generator.WarmupService;
import com.example.fraud.graph.GraphService;
import com.example.fraud.metadata.AerospikeMetadataManager;
import org.springframework.stereotype.Service;

@Service
public class ServiceOrchestrator {
    private final WarmupService warmupService;
    private final GeneratorService generatorService;
    private final GraphService graphService;
    private final FraudService fraudService;
    private final AerospikeMetadataManager metadataManager;

    public ServiceOrchestrator(WarmupService warmupService,
                               GeneratorService generatorService,
                               FraudService fraudService,
                               GraphService graphService,
                               AerospikeMetadataManager metadataManager) {
        this.warmupService = warmupService;
        this.generatorService = generatorService;
        this.graphService = graphService;
        this.fraudService = fraudService;
        this.metadataManager = metadataManager;
        runWarmupFlow();
    }

    public void runWarmupFlow() {
        warmupService.runWarmup();
    }

    public void runShutdownFLow() {
        generatorService.shutdown();
        fraudService.shutdown();
        metadataManager.shutdown();
        graphService.shutdown();
    }
}