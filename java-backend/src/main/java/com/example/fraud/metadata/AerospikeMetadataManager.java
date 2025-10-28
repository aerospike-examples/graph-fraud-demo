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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import com.aerospike.client.AerospikeClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class AerospikeMetadataManager {
    private static final Logger logger = LoggerFactory.getLogger(AerospikeMetadataManager.class);
    private static final int LATCH_SIZE = 200;
    private static final int LATCH_BREAK_TIME_MILLISECONDS = 1000;
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
    private final CountDownLatch latch = new CountDownLatch(LATCH_SIZE);
    private final AtomicInteger totalCount;
    private boolean exit = false;

    private AerospikeMetadataManager(MetadataProperties props, Map<String, AerospikeMetadata> metadataMap,
                                     AerospikeClient client, WritePolicy writePolicy) {
        scheduler.scheduleAtFixedRate(this::writeAsync, LATCH_BREAK_TIME_MILLISECONDS, LATCH_BREAK_TIME_MILLISECONDS, TimeUnit.MILLISECONDS);
        this.client = client;
        String namespace = props.getNamespace();
        String setName = props.getSetName();
        this.writePolicy = writePolicy;
        this.props = props;
        this.totalCount = new AtomicInteger(0);
        this.metadataMap = metadataMap;
        for (AerospikeMetadata metadata : metadataMap.values()) {
            metadata.setKey(namespace, setName);
        }
        this.writeDefaultsIfNone();
    }

    private void writeDefaultsIfNone() {
        WritePolicy createOnly = new WritePolicy(writePolicy);
        createOnly.recordExistsAction = RecordExistsAction.CREATE_ONLY;

        for (AerospikeMetadata m : metadataMap.values()) {
            Map<String, Long> defaults = m.getBinDefaults();
            if (defaults == null || defaults.isEmpty()) continue;

            Key key = new Key(props.getNamespace(), props.getSetName(), m.getName());

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

    public void shutdown() {
        scheduler.shutdown();
        writeExecutor.shutdown();
        exit = true;
        for (int i = 0; i < LATCH_SIZE; i++) {
            latch.countDown();
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
        if (totalCount.incrementAndGet() >= LATCH_SIZE) writeAsync();
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
            final Key key = new Key(props.getNamespace(), props.getSetName(), metadata.getName());
            for (Map.Entry<String, Long> entry : snapshot.entrySet()) {
                ops.add(Operation.add(new Bin(entry.getKey(), entry.getValue())));
            }
            client.operate(writePolicy, key, ops.toArray(new Operation[0]));
        } catch (AerospikeException e) {
            throw new RuntimeException("Could not write Metadata Metric", e);
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
