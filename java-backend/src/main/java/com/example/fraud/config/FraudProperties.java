package com.example.fraud.config;

import com.example.fraud.model.AutoFlagMode;
import java.util.Arrays;
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
    private final boolean autoFlagEnabled;
    private final int autoFlagFraudScoreThreshold;
    private final AutoFlagMode autoFlagMode;

    public FraudProperties(
            Integer fraudWorkerPoolSize,
            @Nullable Integer fraudWorkerMaxPoolSize,
            @Nullable Integer autoFlagFraudScoreThreshold,
            @Nullable Boolean autoFlagEnabled,
            @Nullable String autoFlagMode
    ) {
        this.fraudWorkerMaxPoolSize = fraudWorkerMaxPoolSize != null
                ? fraudWorkerMaxPoolSize : fraudWorkerPoolSize;
        this.fraudWorkerPoolSize = fraudWorkerPoolSize;
        this.autoFlagEnabled = Boolean.TRUE.equals(autoFlagEnabled);
        this.autoFlagFraudScoreThreshold = autoFlagFraudScoreThreshold != null
            ? autoFlagFraudScoreThreshold : 100;
        if (this.autoFlagEnabled) {
            this.autoFlagMode = parseAutoFlagMode(autoFlagMode);
        } else {
            this.autoFlagMode = null;
        }
    }

    private AutoFlagMode parseAutoFlagMode(String mode) {
        if (mode == null) {
            throw new IllegalArgumentException("Auto-flag mode is null. \n Must be one of " + Arrays.toString(AutoFlagMode.values()));
        }
        try {
            return AutoFlagMode.valueOf(mode.toUpperCase());
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("Invalid auto-flag mode: " + mode + "\n Must be one of " + Arrays.toString(AutoFlagMode.values()));
        }
    }
}