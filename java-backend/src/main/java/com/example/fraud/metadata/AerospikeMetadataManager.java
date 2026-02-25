package com.example.fraud.metadata;


import com.aerospike.client.AerospikeException;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Operation;
import com.aerospike.client.Record;
import com.aerospike.client.ResultCode;

import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.example.fraud.config.MetadataProperties;
import com.example.fraud.model.MetadataRecord;
import jakarta.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import com.aerospike.client.AerospikeClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

@Component
public class AerospikeMetadataManager {
    private static final Logger logger = LoggerFactory.getLogger(AerospikeMetadataManager.class);
    private final int flushThreshold;
    private final int flushIntervalMs;
    private final AerospikeClient client;
    private final WritePolicy writePolicy;
    private final Map<String, AerospikeMetadata> metadataMap;
    private final MetadataProperties props;
    private final AtomicBoolean writing = new AtomicBoolean(false);
    private final ExecutorService writeExecutor = Executors.newSingleThreadExecutor(r -> {
        Thread t = Executors.defaultThreadFactory().newThread(r);
        t.setDaemon(true);
        return t;
    });
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = Executors.defaultThreadFactory().newThread(r);
        t.setDaemon(true);
        return t;
    });
    private final AtomicInteger totalCount;

    private AerospikeMetadataManager(MetadataProperties props, Map<String, AerospikeMetadata> metadataMap,
                                     AerospikeClient client, WritePolicy writePolicy, Environment env) {
        this.client = client;
        this.writePolicy = writePolicy;
        this.props = props;
        this.flushThreshold = props.getFlushThreshhold();
        this.flushIntervalMs = props.getFlushIntervalMs();
        this.totalCount = new AtomicInteger(0);
        this.metadataMap = metadataMap;
        for (AerospikeMetadata metadata : metadataMap.values()) {
            metadata.setKey(props.getNamespace(), props.getSetName());
        }
        this.writeDefaultsIfNone();
        scheduler.scheduleAtFixedRate(this::writeAsync, flushIntervalMs, flushIntervalMs, TimeUnit.MILLISECONDS);
    }

    public void writeDefaultsIfNone() {
        WritePolicy createOnly = new WritePolicy(writePolicy);
        createOnly.recordExistsAction = RecordExistsAction.CREATE_ONLY;

        for (AerospikeMetadata m : metadataMap.values()) {
            Map<String, Long> defaults = m.getBinDefaults();
            if (defaults == null || defaults.isEmpty()) continue;

            Key key = m.getKey();

            Bin[] bins = new Bin[defaults.size()];
            int i = 0;
            for (Map.Entry<String, Long> e : defaults.entrySet()) {
                bins[i++] = new Bin(e.getKey(), e.getValue());
            }

            try {
                client.put(createOnly, key, bins);
            } catch (AerospikeException ae) {
                if (ae.getResultCode() != ResultCode.KEY_EXISTS_ERROR) throw ae;
            }
        }
    }



    public Map<String, Object> readRecord(final MetadataRecord metadataRecord) {
        Record record = metadataMap.get(metadataRecord.getValue()).getRecord(client);
        if (record == null) {
            return Map.of();
        }
        return record.bins;
    }

    public void incrementCount(final MetadataRecord record, final String bin, long count) {
        AerospikeMetadata metadata = metadataMap.get(record.getValue());
        if (metadata == null) throw new IllegalArgumentException("Unknown metadata: " + record.getValue());
        metadata.incrementBin(bin, count);
        if (totalCount.incrementAndGet() >= flushThreshold) writeAsync();
    }

    private void writeAsync() { writeExecutor.submit(this::doWrite); }

    private void doWrite() {
        if (!writing.compareAndSet(false, true)) return;
        try {
            metadataMap.values().forEach(this::doWriteOne);
            totalCount.set(0);
        } finally { writing.set(false); }
    }

    private void doWriteOne(AerospikeMetadata metadata) {
        Map<String, Long> snapshot = metadata.drainSnapshot();
        List<Operation> ops = new ArrayList<>();
        if (snapshot.isEmpty()) return;
        try {
            final Key key = metadata.getKey();
            for (Map.Entry<String, Long> entry : snapshot.entrySet()) {
                ops.add(Operation.add(new Bin(entry.getKey(), entry.getValue())));
            }
            client.operate(writePolicy, key, ops.toArray(new Operation[0]));
        } catch (AerospikeException e) {
            throw new RuntimeException("Could not write Metadata Metric", e);
        }
    }

    @PreDestroy
    public void shutdown() {
        try {
            scheduler.shutdown();
            doWrite();
        } finally {
            writeExecutor.shutdown();
            try {
                scheduler.awaitTermination(2, TimeUnit.SECONDS);
                writeExecutor.awaitTermination(3, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                scheduler.shutdownNow();
                writeExecutor.shutdownNow();
            }
        }

    }

    public void clear() {
        try {
            client.truncate(null, props.getNamespace(), props.getSetName(), null);
            logger.info("Truncated set '{}' in namespace '{}'", props.getSetName(), props.getNamespace());
        } catch (AerospikeException e) {
            throw new RuntimeException("Failed to truncate set " + props.getSetName(), e);
        }
    }
}
