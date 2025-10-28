package com.example.fraud.metadata;

import com.aerospike.client.Bin;
import com.example.fraud.graph.GraphService;
import java.util.concurrent.atomic.LongAdder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component("user")
public class UserMetadata extends AerospikeMetadata {

    protected UserMetadata(@Value("${metadata.userMetadataName:user}") String metadataName) {
        super(metadataName);
        // generator calculates risk_score as round(rnd.uniform(0, 100), 1)
        Long users = 20000L;
        binToCount.put("critical", new LongAdder());
        binToCount.put("high", new LongAdder());
        binToCount.put("medium", new LongAdder());
        binToCount.put("low", new LongAdder());
        Long defaultCritical = (long) (users * .2495); // 75-100
        Long defaultHigh = (long) (users * .25);
        Long defaultMedium = (long) (users * .25);
        Long defaultLow = (long) (users * .2495);

        binDefaults.put("critical", defaultCritical);
        binDefaults.put("high", defaultHigh);
        binDefaults.put("medium", defaultMedium);
        binDefaults.put("low", defaultLow);
    }
}
