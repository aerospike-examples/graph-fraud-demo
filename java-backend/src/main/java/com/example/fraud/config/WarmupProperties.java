package com.example.fraud.config;

import java.time.Duration;
import java.time.temporal.ChronoUnit;
import lombok.Getter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.convert.DurationUnit;
import org.springframework.lang.Nullable;
import org.springframework.validation.annotation.Validated;

@Getter
@Validated
@ConfigurationProperties(prefix = "warmup")
public class WarmupProperties {

    private final boolean enabled;
    private final Duration time;
    private final int paralellism;

    public WarmupProperties(
            @Nullable Boolean enabled,
            @Nullable Integer paralellism,
            @DurationUnit(ChronoUnit.SECONDS) @Nullable Duration time
    ) {
        this.enabled = (enabled != null) ? enabled : false;
        this.time = (time != null) ? time : Duration.ofSeconds(30);
        this.paralellism = (paralellism != null) ? paralellism : 64;
    }
}