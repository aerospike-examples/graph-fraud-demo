package com.example.fraud.config;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.WritePolicy;
import lombok.Getter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.validation.annotation.Validated;

@Getter
@Validated
@ConfigurationProperties(prefix = "metadata")
public class MetadataProperties {
    private final String namespace;
    private final String setName;
    private final String aerospikeAddress;
    private final Integer flushIntervalMs;
    private final Integer flushThreshhold;

    public MetadataProperties(String namespace, String setName, String aerospikeAddress,
                              Integer flushIntervalMs, Integer flushThreshhold) {
        this.namespace = namespace;
        this.setName = setName;
        this.aerospikeAddress = aerospikeAddress;
        this.flushIntervalMs = flushIntervalMs;
        this.flushThreshhold = flushThreshhold;
    }

    @Bean(destroyMethod = "close")
    public AerospikeClient aerospikeClient() {
        return new AerospikeClient(this.getAerospikeAddress(), 3000);
    }

    @Bean
    public WritePolicy writePolicy() {
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        return wp;
    }
}
