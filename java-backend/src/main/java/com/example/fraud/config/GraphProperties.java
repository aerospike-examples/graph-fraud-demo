package com.example.fraud.config;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Validated
@ConfigurationProperties(prefix = "graph")
public record GraphProperties(@Positive @NotNull Integer mainConnectionPoolSize,
                              @Positive @NotNull Integer fraudConnectionPoolSize,
                              @NotNull String gremlinHost,
                              @NotNull Integer gremlinPort) {
}