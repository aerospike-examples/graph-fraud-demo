package com.example.fraud.metadata;

import java.util.concurrent.atomic.LongAdder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component("user")
public class UserMetadata extends AerospikeMetadata {

    protected UserMetadata(@Value("${metadata.userMetadataName:user}") String metadataName,
                           @Value("${metadata.userMetadataCount:20000L}") Long userCount,
                           @Value("${metadata.userMetadataHighChance:.25}") double highChance,
                           @Value("${metadata.userMetadataMediumChance:.45}") double mediumChance,
                           @Value("${metadata.userMetadataLowChance:.3}") double lowChance) {
        super(metadataName);
        // generator calculates risk_score as round(rnd.uniform(0, 100), 1)
        binToCount.put("high", new LongAdder());
        binToCount.put("medium", new LongAdder());
        binToCount.put("low", new LongAdder());
        Long defaultHigh = (long) (userCount * highChance);
        Long defaultMedium = (long) (userCount * mediumChance);
        Long defaultLow = (long) (userCount * lowChance);

        binDefaults.put("high", defaultHigh);
        binDefaults.put("medium", defaultMedium);
        binDefaults.put("low", defaultLow);
    }
}
