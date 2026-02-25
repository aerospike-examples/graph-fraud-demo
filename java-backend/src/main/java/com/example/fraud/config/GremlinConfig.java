package com.example.fraud.config;

import com.example.fraud.graph.GraphService;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class GremlinConfig {

    @Bean(name = "fraudG")
    public GraphTraversalSource fraudTraversal(GraphService graphService) {
        return graphService.getFraudClient();
    }

    @Bean(name = "mainG")
    public GraphTraversalSource mainTraversal(GraphService graphService) {
        return graphService.getMainClient();
    }
}