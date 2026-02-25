package com.example.fraud.metadata;

import java.util.concurrent.atomic.LongAdder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component("fraud")
public class FraudMetadata extends AerospikeMetadata {
    protected FraudMetadata(@Value("${metadata.fraudMetadataName:fraud}") String metadataName) {
        super(metadataName);
        binDefaults.put("amount", 0L);
        binDefaults.put("total", 0L);
        binDefaults.put("blocked", 0L);
        binDefaults.put("review", 0L);
        binToCount.put("amount", new LongAdder());
        binToCount.put("total", new LongAdder());
        binToCount.put("blocked", new LongAdder());
        binToCount.put("review", new LongAdder());
    }
}
