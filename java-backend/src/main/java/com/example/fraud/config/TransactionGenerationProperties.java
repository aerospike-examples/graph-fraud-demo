package com.example.fraud.config;

import jakarta.validation.constraints.Null;
import java.time.Duration;
import java.time.temporal.ChronoUnit;
import lombok.Getter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.convert.DurationUnit;
import org.springframework.lang.Nullable;
import org.springframework.validation.annotation.Validated;

@Getter
@Validated
@ConfigurationProperties(prefix = "generation")
public class TransactionGenerationProperties {
    private final int transactionWorkerPoolSize;
    private final int transactionWorkerMaxPoolSize;
    private final long transactionWorkerExecutorKeepAliveTime;
    private final int transactionSchedulerTpsCapacity;
    private final int maxTransactionRate;

    public TransactionGenerationProperties(
            Integer transactionWorkerPoolSize,
            @Nullable Integer transactionWorkerMaxPoolSize,
            @Nullable Integer transactionSchedulerTpsCapacity,
            @Nullable Long transactionWorkerExecutorKeepAliveTime,
            @Nullable Integer maxTransactionRate
    ) {
        this.transactionWorkerPoolSize = transactionWorkerPoolSize;
        this.transactionWorkerMaxPoolSize = transactionWorkerMaxPoolSize != null
                ? transactionWorkerMaxPoolSize : transactionWorkerPoolSize;
        this.transactionWorkerExecutorKeepAliveTime = transactionWorkerExecutorKeepAliveTime != null
                ? transactionWorkerExecutorKeepAliveTime : 60L;
        this.transactionSchedulerTpsCapacity = transactionSchedulerTpsCapacity != null
                ? transactionSchedulerTpsCapacity : 100;
        this.maxTransactionRate = maxTransactionRate != null
                ? maxTransactionRate : 4000;
    }
}
