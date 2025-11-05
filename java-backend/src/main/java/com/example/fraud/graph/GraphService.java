package com.example.fraud.graph;

import com.example.fraud.config.GraphProperties;
import com.example.fraud.fraud.PerformanceInfo;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.metadata.AerospikeMetadataManager;
import com.example.fraud.fraud.RecentTransactions;
import com.example.fraud.model.MetadataRecord;
import com.example.fraud.model.TransactionType;
import com.example.fraud.model.UserRiskStatus;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.UUID;
import org.apache.tinkerpop.gremlin.driver.Cluster;
import org.apache.tinkerpop.gremlin.driver.remote.DriverRemoteConnection;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;
import org.apache.tinkerpop.gremlin.structure.T;
import org.apache.tinkerpop.gremlin.process.traversal.Order;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Service;

import static org.apache.tinkerpop.gremlin.process.traversal.AnonymousTraversalSource.traversal;

@Service
public class GraphService {

    private static final Logger logger = LoggerFactory.getLogger(GraphService.class);
    final private GraphProperties props;
    private Cluster fraudCluster;
    private Cluster mainCluster;
    private GraphTraversalSource fraudG;
    private GraphTraversalSource mainG;
    private final AerospikeMetadataManager metadataManager;
    private final RecentTransactions recentTransactions;


    public GraphService(GraphProperties graphProperties, AerospikeMetadataManager metadataManager,
                        RecentTransactions recentTransactions) {
        this.props = graphProperties;
        this.metadataManager = metadataManager;
        this.recentTransactions = recentTransactions;
        connect();
    }

    private void connect() {
        try {
            logger.info("Connecting to Aerospike Graph: {}", (Object) props.gremlinHosts());

            Cluster.Builder mainBuilder = Cluster.build();
            String[] hosts = props.gremlinHosts().split(",");
            for (String host : hosts) {
                mainBuilder.addContactPoint(host);
            }
            mainBuilder
                    .port(props.gremlinPort())
                    .connectionSetupTimeoutMillis(500)
                    .create();
            mainCluster = mainBuilder.create();
            logger.info("main cluster created");

            Cluster.Builder builder = Cluster.build();
            for (String host : hosts) {
                builder.addContactPoint(host);
            }
            builder
                    .port(props.gremlinPort())
                    .connectionSetupTimeoutMillis(500)
                    .maxConnectionPoolSize(props.mainConnectionPoolSize())
                    .minConnectionPoolSize(props.mainConnectionPoolSize())
                    .create();
            fraudCluster = builder.create();
            logger.info("fraud cluster created");

            mainG = traversal().withRemote(DriverRemoteConnection.using(mainCluster));
            fraudG = traversal().withRemote(DriverRemoteConnection.using(fraudCluster));
            logger.info("Sources set up");

            healthCheck();

            logger.info("Connected to Aerospike Graph Service");

            warmRecentTransactions();

        } catch (Exception e) {
            logger.error("Could not connect to Aerospike Graph: {}", e.getMessage());
            logger.error("Graph database connection is required. Please ensure Aerospike Graph is running on port {}",
                    props.gremlinPort());
            throw new RuntimeException("Failed to connect to Aerospike Graph", e);
        }
    }

    private void warmRecentTransactions() {
        if (mainG == null) return;
        try {
            List<Object> ids = mainG.with("evaluationTimeout", 15000)
                    .E()
                    .hasLabel("TRANSACTS")
                    .limit(100)
                    .id()
                    .toList();
            if (ids == null || ids.isEmpty()) {
                logger.info("Recent transactions warm-up: no existing transactions found");
                return;
            }
            for (Object id : ids) {
                recentTransactions.add(id);
            }
            logger.info("Recent transactions warm-up loaded {} entries", ids.size());
        } catch (Exception e) {
            logger.warn("Recent transactions warm-up skipped: {}", e.getMessage());
        }
    }

    public boolean healthCheck() {
        logger.info("Running healthcheck on main cluster");
        int mainResult = mainG.inject(0).next();

        logger.info("Running healthcheck on fraud cluster");
        int fraudResult = fraudG.inject(0).next();

        if (mainResult != 0) {
            return false;
        }
        if (fraudResult != 0) {
            return false;
        }
        return true;
    }

    public void shutdown() {
        if (mainCluster != null) {
            try {
                mainCluster.close();
                logger.info("Disconnected from Aerospike Graph (main)");
            } catch (Exception e) {
                logger.warn("Error closing main connection: {}", e.getMessage());
            }
        }
        if (fraudCluster != null) {
            try {
                fraudCluster.close();
                logger.info("Disconnected from Aerospike Graph (fraud)");
            } catch (Exception e) {
                logger.warn("Error closing fraud connection: {}", e.getMessage());
            }
        }
    }

    public GraphTraversalSource getMainClient() {
        return mainG;
    }

    public GraphTraversalSource getFraudClient() {
        return fraudG;
    }

    public Map<String, Object> getGraphSummary() {
        try {
            if (mainG == null) {
                logger.warn("No graph client available for summary");
                return new HashMap<>();
            }

            logger.info("Getting graph summary using Aerospike Graph admin API");
            @SuppressWarnings("unchecked")
            Map<String, Object> summaryResult = (Map<String, Object>)
                    mainG.call("aerospike.graph.admin.metadata.summary").next();

            logger.debug("Raw graph summary result: {}", summaryResult);

            Map<String, Object> parsedSummary = new HashMap<>();
            parsedSummary.put("total_vertex_count", summaryResult.getOrDefault("Total vertex count", 0));
            parsedSummary.put("total_edge_count", summaryResult.getOrDefault("Total edge count", 0));
            parsedSummary.put("total_supernode_count", summaryResult.getOrDefault("Total supernode count", 0));
            parsedSummary.put("vertex_counts", summaryResult.getOrDefault("Vertex count by label", new HashMap<>()));
            parsedSummary.put("edge_counts", summaryResult.getOrDefault("Edge count by label", new HashMap<>()));
            parsedSummary.put("supernode_counts", summaryResult.getOrDefault("Supernode count by label", new HashMap<>()));
            parsedSummary.put("vertex_properties", summaryResult.getOrDefault("Vertex properties by label", new HashMap<>()));
            parsedSummary.put("edge_properties", summaryResult.getOrDefault("Edge properties by label", new HashMap<>()));
            parsedSummary.put("raw_summary", summaryResult);

            logger.info("Parsed graph summary - Vertices: {}, Edges: {}",
                    parsedSummary.get("total_vertex_count"),
                    parsedSummary.get("total_edge_count"));

            return parsedSummary;

        } catch (Exception e) {
            logger.error("Error getting graph summary: {}", e.getMessage());
            return new HashMap<>();
        }
    }

    public long getAccountCount() {
        if (mainG == null) {
            logger.warn("No graph client available for summary");
            return 0;
        }

        logger.info("Getting graph summary using Aerospike Graph admin API");
        @SuppressWarnings("unchecked")
        Map<String, Object> summaryResult = (Map<String, Object>)
                mainG.call("aerospike.graph.admin.metadata.summary").next();

        logger.debug("Raw graph summary result: {}", summaryResult);
        Map<String, Object> parsedSummary = (Map<String, Object>) summaryResult.getOrDefault("Vertex count by label", new HashMap<>());
        return (long) parsedSummary.getOrDefault("account", 0L);
    }

    public long getUserCount() {
        if (mainG == null) {
            logger.warn("No graph client available for summary");
            return 0;
        }

        logger.info("Getting graph summary using Aerospike Graph admin API");
        @SuppressWarnings("unchecked")
        Map<String, Object> summaryResult = (Map<String, Object>)
                mainG.call("aerospike.graph.admin.metadata.summary").next();

        logger.debug("Raw graph summary result: {}", summaryResult);
        Map<String, Object> parsedSummary = (Map<String, Object>) summaryResult.getOrDefault("Vertex count by label", new HashMap<>());
        return (long) parsedSummary.getOrDefault("user", 0L);
    }

    public Map<String, Object> getDashboardStats() {
        try {
            if (mainG == null) {
                throw new RuntimeException("Graph client not available. Cannot get dashboard stats without graph database connection.");
            }

            Map<String, Object> graphSummary = getGraphSummary();

            long users = 0;
            long txns = 0;
            long accounts = 0;
            long devices = 0;

            if (!graphSummary.isEmpty()) {
                @SuppressWarnings("unchecked")
                Map<String, Long> vertices = (Map<String, Long>) graphSummary.get("vertex_counts");
                @SuppressWarnings("unchecked")
                Map<String, Long> edges = (Map<String, Long>) graphSummary.get("edge_counts");

                users = vertices.getOrDefault("user", 0L);
                txns = edges.getOrDefault("TRANSACTS", 0L);
                accounts = vertices.getOrDefault("account", 0L);
                devices = vertices.getOrDefault("device", 0L);

                logger.info("Dashboard stats from summary: users={}, transactions={}, accounts={}, devices={}",
                        users, txns, accounts, devices);
            }

            long flagged = 0;
            double amount = 0.0;
            double fraudRate = 0.0;

            if (txns > 0) {
                try {
                    Map<String, Object> bins = metadataManager.readRecord(MetadataRecord.FRAUD);
                    long blocked = ((Number) bins.getOrDefault("blocked", 0L)).longValue();
                    long reviewed = ((Number) bins.getOrDefault("reviewed", 0L)).longValue();
                    flagged = blocked + reviewed;
                    amount = ((Number) bins.getOrDefault("amount", 0.0)).longValue();
                    fraudRate = (flagged / (double) txns) * 100.0;

                } catch (Exception e) {
                    logger.warn("Error getting detailed transaction stats: {}", e.getMessage());
                }
            }

            Map<String, Object> stats = new HashMap<>();
            stats.put("users", users);
            stats.put("txns", txns);
            stats.put("flagged", flagged);
            stats.put("amount", amount);
            stats.put("devices", devices);
            stats.put("accounts", accounts);
            stats.put("fraud_rate", fraudRate);
            stats.put("health", "connected");

            return stats;

        } catch (Exception e) {
            logger.error("Error getting dashboard stats: {}", e.getMessage());
            Map<String, Object> errorStats = new HashMap<>();
            errorStats.put("users", 0);
            errorStats.put("txns", 0);
            errorStats.put("flagged", 0);
            errorStats.put("amount", 0.0);
            errorStats.put("fraud_rate", 0.0);
            errorStats.put("health", "error");
            return errorStats;
        }
    }

    public Map<String, Object> getUserStats() {
        try {
            if (mainG == null) {
                throw new RuntimeException("Graph client not available. Cannot get users without graph database connection.");
            }

            Map<String, Object> bins = metadataManager.readRecord(MetadataRecord.USERS);
            long high = (long) bins.getOrDefault("high", 0L);
            long medium = (long) bins.getOrDefault("medium", 0L);
            long low = (long) bins.getOrDefault("low", 0L);

            Map<String, Object> stats = new HashMap<>();
            stats.put("total_users", getUserCount());
            stats.put("total_low_risk", high);
            stats.put("total_med_risk", medium);
            stats.put("total_high_risk", low);

            return stats;

        } catch (Exception e) {
            logger.error("Error getting user stats: {}", e.getMessage());
            Map<String, Object> errorStats = new HashMap<>();
            errorStats.put("total_users", 0);
            errorStats.put("total_low_risk", 0);
            errorStats.put("total_med_risk", 0);
            errorStats.put("total_high_risk", 0);
            return errorStats;
        }
    }

    public Map<String, Object> getTransactionStats() {
        try {
            if (mainG == null) {
                throw new RuntimeException("Graph client not available. Cannot get transactions without graph database connection.");
            }
            Map<String, Object> bins = metadataManager.readRecord(MetadataRecord.FRAUD);
            long total = (long) bins.getOrDefault("total", 0L);
            long blocked = (long) bins.getOrDefault("blocked", 0L);
            long review = (long) bins.getOrDefault("review", 0L);

            Map<String, Object> stats = new HashMap<>();
            stats.put("total_txns", total);
            stats.put("total_blocked", blocked);
            stats.put("total_review", review);
            stats.put("total_clean", total - blocked - review);
            return stats;

        } catch (Exception e) {
            logger.error("Error getting transaction stats: {}", e.getMessage());
            Map<String, Object> errorStats = new HashMap<>();
            errorStats.put("total_txns", 0);
            errorStats.put("total_blocked", 0);
            errorStats.put("total_review", 0);
            errorStats.put("total_clean", 0);
            return errorStats;
        }
    }

    public TransactionInfo createTransaction(String fromId, String toId,
                                             double amount, TransactionType type,
                                             String genType,
                                             String location, Instant start) {
        try {
            if (mainG == null) {
                throw new RuntimeException("Graph client not available");
            }


            if (fromId.equals(toId)) {
                throw new RuntimeException("Source and destination accounts cannot be the same");
            }

            String txnId = UUID.randomUUID().toString();

            Object edgeId = mainG.V(fromId)
                    .addE("TRANSACTS")
                    .to(__.V(toId))
                    .property("txn_id", txnId)
                    .property("amount", Math.round(amount * 100.0) / 100.0)
                    .property("currency", "USD")
                    .property("type", type.getValue())
                    .property("method", "electronic_transfer")
                    .property("location", location)
                    .property("timestamp", Instant.now().toString())
                    .property("status", "completed")
                    .property("gen_type", genType)
                    .id()
                    .next();
            metadataManager.incrementCount(MetadataRecord.FRAUD, "amount", (long) amount);
            metadataManager.incrementCount(MetadataRecord.FRAUD, "total", 1L);
            recentTransactions.add(edgeId);

            logger.debug("{} transaction created: {} from {} to {} amount {}",
                    genType, txnId, fromId, toId, amount);
            return new TransactionInfo(true, edgeId, txnId, fromId, toId, amount,
                    new PerformanceInfo(start, Duration.between(start, Instant.now()), true));
        } catch (Exception e) {
            logger.error("Error creating transaction: {}", e.getMessage());
            return new TransactionInfo(false, null, null, null, null, -1,
                    new PerformanceInfo(start, Duration.between(start, Instant.now()), false));
        }
    }

    public TransactionInfo createManualTransaction(String fromId, String toId, double amount,
                                                   TransactionType type, String genType, String location, Instant start) {
        return createTransaction(fromId, toId, amount, type, genType, location, start);
    }


    public Map<String, Object> getUserSummary(String userId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                logger.error("No graph client available. Cannot get user summary without graph connection.");
                return null;
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> userSummary = g.V(userId)
                    .project("user", "accounts", "txns", "total_txns", "total_sent", "total_recd", "devices", "connected_users")
                    .by(__.elementMap())
                    .by(__.out("OWNS").elementMap().fold())
                    .by(__.out("OWNS").bothE("TRANSACTS").order().by("timestamp", Order.desc).limit(10)
                            .project("txn", "other_party")
                            .by(__.elementMap())
                            .by(__.bothV().in("OWNS").where(__.not(__.hasId(userId))).elementMap())
                            .fold())
                    .by(__.out("OWNS").bothE("TRANSACTS").count())
                    .by(__.coalesce(__.out("OWNS").inE("TRANSACTS").values("amount").sum(), __.constant(0.00)))
                    .by(__.coalesce(__.out("OWNS").outE("TRANSACTS").values("amount").sum(), __.constant(0.00)))
                    .by(__.out("USES").elementMap().fold())
                    .by(__.out("USES").in("USES").not(__.hasId(userId)).fold())
                    .next();

            if (userSummary == null) return null;

            @SuppressWarnings("unchecked")
            Map<Object, Object> userMap = (Map<Object, Object>) userSummary.get("user");
            if (userMap != null) {
                Map<String, Object> normalized = new LinkedHashMap<>();
                for (Map.Entry<Object, Object> e : userMap.entrySet()) {
                    if (T.id.equals(e.getKey())) {
                        normalized.put("id", e.getValue());
                    } else if (!T.label.equals(e.getKey())) {
                        normalized.put(String.valueOf(e.getKey()), e.getValue());
                    }
                }
                userSummary.put("user", normalized);

                Object rs = normalized.getOrDefault("risk_score", 0.0);
                double riskScore = (rs instanceof Number) ? ((Number) rs).doubleValue() : 0.0;
                String riskLevel = UserRiskStatus.evaluateRiskScore(riskScore).toString();
                userSummary.put("risk_level", riskLevel);
            }

            return userSummary;

        } catch (Exception e) {
            logger.error("Error getting user summary", e);
            return null;
        }
    }

    public Map<String, Object> getTransactionSummary(String txnEdgeId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                throw new IllegalStateException("Graph client not available. Cannot get transaction detail.");
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> detail = (Map<String, Object>) g.E(txnEdgeId)
                    .project("txn", "src", "dest")
                    .by(__.elementMap())
                    .by(__.outV()
                            .project("account", "user")
                            .by(__.elementMap())
                            .by(__.in("OWNS").elementMap()))
                    .by(__.inV()
                            .project("account", "user")
                            .by(__.elementMap())
                            .by(__.in("OWNS").elementMap()))
                    .next();

            if (detail == null) return null;

            Map<String, Object> out = new LinkedHashMap<>();
            out.put("txn", detail.get("txn"));
            out.put("src", detail.get("src"));
            out.put("dest", detail.get("dest"));
            return out;

        } catch (Exception e) {
            logger.error("Error getting transaction detail", e);
            return null;
        }
    }

    public boolean flagAccount(Object accountId, String reason) {
        try {
            GraphTraversalSource g = getMainClient();
                g.V(accountId)
                        .property("fraud_flag", true)
                        .property("flag_reason", reason)
                        .property("flag_timestamp", Instant.now().toString())
                        .iterate();
            metadataManager.incrementCount(MetadataRecord.ACCOUNTS, "flagged", 1);
            logger.info("Account {} flagged as fraudulent: {}", accountId, reason);
            return true;

        } catch (Exception e) {
            logger.error("Error flagging account {}", accountId, e);
            return false;
        }
    }

    public boolean unflagAccount(Object accountId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) throw new IllegalStateException("Graph client not available");

            g.V(accountId)
                    .property("fraud_flag", false)
                    .property("unflagTimestamp", Instant.now().toString())
                    .iterate();
            metadataManager.incrementCount(MetadataRecord.ACCOUNTS, "flagged", -1);
            logger.info("Account {} unflagged", accountId);
            return true;

        } catch (Exception e) {
            logger.error("Error unflagging account {}", accountId, e);
            return false;
        }
    }

    public void seedSampleData() {
        mainG.V().drop().iterate();
        metadataManager.clear();
        metadataManager.writeDefaultsIfNone();
        String verticesPath = props.verticesPath();
        String edgesPath = props.edgesPath();

        logger.info("Bulk load Starting");
        mainG.with("evaluationTimeout", 120000)
                .call("aerospike.graphloader.admin.bulk-load.load")
                .with("aerospike.graphloader.vertices", verticesPath)
                .with("aerospike.graphloader.edges", edgesPath)
                .with("aerospike.graphloader.gcs-keyfile", "/opt/secrets/gcs-keyfile.json")
                .with("incremental_load", false)
                .next();

        logger.info("Bulk load status:");
        while (true) {
            Map<String, Object> status = getBulkloadStatus();
            logger.info("{}", status);

            if (Objects.equals(status.get("complete"), true)) {
                logger.info("Bulk load data seeding completed!");
                break;
            }
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                logger.warn("Bulk load wait interrupted", e.getMessage());
            }

        }
    }

    public Map<String, Object> getBulkloadStatus() {
        return (Map<String, Object>)
                mainG.call("aerospike.graphloader.admin.bulk-load.status").next();
    }

    public void dropAll() {
            mainG.V().drop().iterate();
            metadataManager.clear();
            metadataManager.writeDefaultsIfNone();
    }

    public boolean accountExists(String accountId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) return false;
            long cnt = g.V(accountId).count().next();
            return cnt > 0;
        } catch (Exception e) {
            logger.warn("accountExists check failed for {}: {}", accountId, e.getMessage());
            return false;
        }
    }

    public List<Map<String, Object>> getTransactionsSummaryByIds(List<Object> edgeIds) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null || edgeIds == null || edgeIds.isEmpty()) return List.of();
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> rows = g.E(edgeIds.toArray())
                    .project("id", "txn_id", "amount", "timestamp", "location", "fraud_score", "fraud_status", "sender", "receiver")
                    .by(__.id())
                    .by(__.values("txn_id").fold().coalesce(__.unfold(), __.constant("")))
                    .by(__.values("amount").fold().coalesce(__.unfold(), __.constant(0)))
                    .by(__.values("timestamp").fold().coalesce(__.unfold(), __.constant("")))
                    .by(__.values("location").fold().coalesce(__.unfold(), __.constant("")))
                    .by(__.values("fraud_score").fold().coalesce(__.unfold(), __.constant(0)))
                    .by(__.values("fraud_status").fold().coalesce(__.unfold(), __.constant("")))
                    .by(__.outV().id())
                    .by(__.inV().id())
                    .toList();
            return rows;
        } catch (Exception e) {
            logger.error("Error building transactions summary: {}", e.getMessage());
            return List.of();
        }
    }

    public List<Map<String, Object>> getUsersSummary(List<String> userIds) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null || userIds == null || userIds.isEmpty()) return List.of();
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> rows = g.V(userIds.toArray())
                    .project("id", "name", "email", "risk_score", "age", "location", "signup_date")
                    .by(__.id())
                    .by(__.values("name").fold().coalesce(__.unfold(), __.constant("")))
                    .by(__.values("email").fold().coalesce(__.unfold(), __.constant("")))
                    .by(__.values("risk_score").fold().coalesce(__.unfold(), __.constant(0)))
                    .by(__.values("age").fold().coalesce(__.unfold(), __.constant(0)))
                    .by(__.values("location").fold().coalesce(__.unfold(), __.constant("")))
                    .by(__.values("signup_date").fold().coalesce(__.unfold(), __.constant("")))
                    .toList();
            return rows;
        } catch (Exception e) {
            logger.error("Error getting users summary: {}", e.getMessage());
            return List.of();
        }
    }
}
