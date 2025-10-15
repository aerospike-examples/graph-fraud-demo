package com.example.fraud.config;

import lombok.Getter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.lang.Nullable;
import org.springframework.validation.annotation.Validated;

@Getter
@Validated
@ConfigurationProperties(prefix = "fraud")
public class FraudProperties {

    private final int fraudWorkerPoolSize;
    private final int fraudWorkerMaxPoolSize;

    public FraudProperties(
            Integer fraudWorkerPoolSize,
            @Nullable Integer fraudWorkerMaxPoolSize
    ) {
        this.fraudWorkerMaxPoolSize = fraudWorkerMaxPoolSize != null
                ? fraudWorkerMaxPoolSize : fraudWorkerPoolSize;
        this.fraudWorkerPoolSize = fraudWorkerPoolSize;
    }
}