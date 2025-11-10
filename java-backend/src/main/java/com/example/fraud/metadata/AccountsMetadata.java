package com.example.fraud.metadata;

import java.util.concurrent.atomic.LongAdder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component("account")
public class AccountsMetadata extends AerospikeMetadata {
    protected AccountsMetadata(@Value("${metadata.accountMetadataName:account}") String metadataName,
                               @Value("${metadata.accountMetadataCount:40000L}") Long accountCount,
                               @Value("${metadata.accountMetadataFlagChance:.1}") double flaggedChance) {
        super(metadataName);
        // Generator states that .1% of accounts are generated as flagged
        long defaultFlaggedAccounts = (long) (accountCount * flaggedChance);
        binDefaults.put("flagged", defaultFlaggedAccounts);
        binToCount.put("flagged", new LongAdder());
    }
}
