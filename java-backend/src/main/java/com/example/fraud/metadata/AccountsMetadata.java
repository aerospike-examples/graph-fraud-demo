package com.example.fraud.metadata;

import java.util.concurrent.atomic.LongAdder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component("account")
public class AccountsMetadata extends AerospikeMetadata {
    protected AccountsMetadata(@Value("${metadata.accountMetadataName:account}") String metadataName) {
        super(metadataName);
        // Generator states that .1% of accounts are generated as flagged
        long accounts = 40000L;
        long defaultFlaggedAccounts = (long) (accounts * .1);
        binDefaults.put("flagged", defaultFlaggedAccounts);
        binToCount.put("flagged", new LongAdder());
    }
}
