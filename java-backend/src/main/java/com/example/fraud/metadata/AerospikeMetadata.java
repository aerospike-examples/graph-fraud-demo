package com.example.fraud.metadata;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;
import lombok.Getter;

public class AerospikeMetadata {
    protected final String metadataName;
    @Getter
    protected final Map<String, Long> binDefaults;
    protected final Map<String, LongAdder> binToCount;
    @Getter
    protected Key key;

    protected AerospikeMetadata(String metadataName) {
        this.metadataName = metadataName;
        this.binDefaults = new ConcurrentHashMap<>();
        this.binToCount = new HashMap<>();
    }

    public Map<String, Long> drainSnapshot() {
        Map<String, Long> out = new HashMap<>();
        binToCount.forEach((s, a) -> { long v = a.sumThenReset(); if (v != 0) out.put(s, v); });
        return out;
    }

    public String getName() {
        return metadataName;
    }

    public void setKey(String namespace, String setName) {
        this.key = new Key(namespace, setName, this.getName());
    }

    public void incrementBin(String binName, long count) {
        binToCount.computeIfAbsent(binName, k -> new LongAdder()).add(count);
    }

    public Record getRecord(AerospikeClient client) {
        return client.get(null, key);
    }
}
