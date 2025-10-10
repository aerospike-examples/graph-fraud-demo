package com.example.fraud.graph;

import com.example.fraud.fraud.TransactionInfo;
import java.time.Instant;
import java.util.UUID;
import org.apache.tinkerpop.gremlin.driver.Cluster;
import org.apache.tinkerpop.gremlin.driver.remote.DriverRemoteConnection;
import org.apache.tinkerpop.gremlin.process.traversal.P;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import static org.apache.tinkerpop.gremlin.process.traversal.AnonymousTraversalSource.traversal;

public class GraphService {

    private static final Logger logger = LoggerFactory.getLogger(GraphService.class);
    private final String[] hosts;
    private final int port;
    private Cluster fraudCluster;
    private Cluster mainCluster;
    private GraphTraversalSource fraudG;
    private GraphTraversalSource mainG;

    public GraphService(String[] hosts, int port, int fraudConnectionPoolWorkers,
                        int mainConnectionPoolWorkers) {
        this.hosts = hosts;
        this.port = port;
        connect(fraudConnectionPoolWorkers,
                mainConnectionPoolWorkers);
    }

    private void connect(int fraudConnectionPoolWorkers,
                         int mainConnectionPoolWorkers) {
        try {
            logger.info("Connecting to Aerospike Graph: {}", (Object) hosts);

            mainCluster = Cluster.build()
                    .addContactPoints(hosts)
                    .port(port)
                    .maxConnectionPoolSize(mainConnectionPoolWorkers)
                    .minConnectionPoolSize(mainConnectionPoolWorkers)
                    .create();

            fraudCluster = Cluster.build()
                    .addContactPoints(hosts)
                    .port(port)
                    .maxConnectionPoolSize(fraudConnectionPoolWorkers)
                    .minConnectionPoolSize(fraudConnectionPoolWorkers)
                    .create();

            mainG = traversal().withRemote(DriverRemoteConnection.using(mainCluster));
            fraudG = traversal().withRemote(DriverRemoteConnection.using(fraudCluster));

            int mainResult = mainG.inject(0).next();
            int fraudResult = fraudG.inject(0).next();

            if (mainResult != 0) {
                throw new RuntimeException("Failed to connect to graph instance on Main Connection");
            }
            if (fraudResult != 0) {
                throw new RuntimeException("Failed to connect to graph instance on Fraud Connection");
            }

            logger.info("Connected to Aerospike Graph Service");

        } catch (Exception e) {
            logger.error("Could not connect to Aerospike Graph: {}", e.getMessage());
            logger.error("Graph database connection is required. Please ensure Aerospike Graph is running on port {}", port);
            throw new RuntimeException("Failed to connect to Aerospike Graph", e);
        }
    }

    public void close() {
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

    public void shutdown() {
        close();
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
                    @SuppressWarnings("unchecked")
                    Map<String, Object> txnStats = (Map<String, Object>) mainG.E()
                            .hasLabel("TRANSACTS")
                            .group("m")
                            .by(__.constant("flagged"))
                            .by(__.has("fraud_score", P.gt(0)).count())
                            .group("m")
                            .by(__.constant("amount"))
                            .by(__.values("amount").sum())
                            .cap("m")
                            .next();

                    flagged = ((Number) txnStats.getOrDefault("flagged", 0L)).longValue();
                    amount = ((Number) txnStats.getOrDefault("amount", 0.0)).doubleValue();
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

            @SuppressWarnings("unchecked")
            List<Number> riskScores = (List<Number>) (List<?>) mainG.V()
                    .hasLabel("user")
                    .values("risk_score")
                    .toList();

            long totalUsers = riskScores.size();
            long lowRisk = riskScores.stream().filter(score -> score.doubleValue() < 25).count();
            long medRisk = riskScores.stream().filter(score -> score.doubleValue() >= 25 && score.doubleValue() < 70).count();
            long highRisk = riskScores.stream().filter(score -> score.doubleValue() >= 70).count();

            Map<String, Object> stats = new HashMap<>();
            stats.put("total_users", totalUsers);
            stats.put("total_low_risk", lowRisk);
            stats.put("total_med_risk", medRisk);
            stats.put("total_high_risk", highRisk);

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

            @SuppressWarnings("unchecked")
            Map<String, Long> stats = (Map<String, Long>) (Map<String, ?>) mainG.E()
                    .hasLabel("TRANSACTS")
                    .fold()
                    .project("total", "blocked", "review")
                    .by(__.unfold().count())
                    .by(__.unfold().has("fraud_status", "blocked").count())
                    .by(__.unfold().has("fraud_status", "review").count())
                    .next();

            long total = stats.getOrDefault("total", 0L);
            long blocked = stats.getOrDefault("blocked", 0L);
            long review = stats.getOrDefault("review", 0L);

            Map<String, Object> result = new HashMap<>();
            result.put("total_txns", total);
            result.put("total_blocked", blocked);
            result.put("total_review", review);
            result.put("total_clean", total - blocked - review);

            return result;

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
                                             double amount, String type,
                                             String genType,
                                             String location) {
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
                    .property("type", type)
                    .property("method", "electronic_transfer")
                    .property("location", location)
                    .property("timestamp", Instant.now().toString())
                    .property("status", "completed")
                    .property("gen_type", genType)
                    .id()
                    .next();
            logger.debug("{} transaction created: {} from {} to {} amount {}",
                    genType, txnId, fromId, toId, amount);
            return new TransactionInfo(true, edgeId, txnId, fromId, toId, amount);
        } catch (Exception e) {
            logger.error("Error creating transaction: {}", e.getMessage());
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", "Error creating transaction: " + e.getMessage());
            return new TransactionInfo(false, null, null, null, null, -1);
        }
    }

    public List<Object> getAccountIds() {

        return mainG.V()
                .hasLabel("account")
                .id()
                .toList();
    }

    public void seedSampleData() throws InterruptedException {
        mainG.V().drop().iterate();
        String verticesPath = "/data/graph_csv/vertices";
        String edgesPath = "/data/graph_csv/edges";

        logger.info("Bulk load Starting");
        mainG.with("evaluationTimeout", 20000)
                .call("aerospike.graphloader.admin.bulk-load.load")
                .with("aerospike.graphloader.vertices", verticesPath)
                .with("aerospike.graphloader.edges", edgesPath)
                .with("incremental_load", false)
                .next();

        logger.info("Bulk load status:");
        while (true) {
            @SuppressWarnings("unchecked")
            Map<String, Object> status = (Map<String, Object>)
                    mainG.call("aerospike.graphloader.admin.bulk-load.status").next();
            logger.info("{}", status);

            if (Objects.equals(status.get("complete"), true)) {
                logger.info("Bulk load data seeding completed!");
                break;
            }
            Thread.sleep(5000);
        }
    }

    public void dropTransactions() throws InterruptedException {
        try {
            while (true) {
                long remaining = 0;
                try {
                    remaining = mainG.with("evaluationTimeout", 20000)
                            .E().hasLabel("TRANSACTS").count().next();
                } catch (Exception e) {
                    logger.warn("dropTransactions count failed (retrying): {}", e.getMessage());
                    remaining = 1;
                }
                if (remaining <= 0) break;

                try {
                    mainG.with("evaluationTimeout", 20000)
                            .E().hasLabel("TRANSACTS")
                            .drop().iterate();
                } catch (Exception e) {
                    logger.warn("dropTransactions chunk failed (retrying): {}", e.getMessage());
                }
                Thread.sleep(250);
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            throw ie;
        }
    }

    public Map<String, Object> inspectIndexes() {
        try {
            if (mainG == null) {
                throw new RuntimeException("Graph client not available");
            }

            Object cardinalityInfo = mainG.call("aerospike.graph.admin.index.cardinality").next();

            Object indexList;
            try {
                indexList = mainG.call("aerospike.graph.admin.index.list").next();
            } catch (Exception e) {
                indexList = "Error getting index list: " + e.getMessage();
            }

            logger.info("Index cardinality: {}", cardinalityInfo);
            logger.info("Index list: {}", indexList);

            Map<String, Object> result = new HashMap<>();
            result.put("cardinality", cardinalityInfo);
            result.put("index_list", indexList);
            result.put("status", "success");
            return result;

        } catch (Exception e) {
            logger.error("Error inspecting indexes: {}", e.getMessage());
            Map<String, Object> result = new HashMap<>();
            result.put("error", e.getMessage());
            result.put("status", "error");
            return result;
        }
    }

    public Map<String, Object> createFraudDetectionIndexes() {
        try {
            if (mainG == null) {
                throw new RuntimeException("Graph client not available");
            }

            List<Map<String, Object>> results = new java.util.ArrayList<>();

            try {
                Object result1 = mainG.call("aerospike.graph.admin.index.create")
                        .with("element_type", "vertex")
                        .with("property_key", "fraud_flag")
                        .next();

                Map<String, Object> indexResult = new HashMap<>();
                indexResult.put("index", "fraud_flag");
                indexResult.put("status", "created");
                indexResult.put("result", result1);
                results.add(indexResult);
                logger.info("Created index: fraud_flag");
            } catch (Exception e) {
                Map<String, Object> indexResult = new HashMap<>();
                indexResult.put("index", "fraud_flag");
                indexResult.put("status", "error");
                indexResult.put("error", e.getMessage());
                results.add(indexResult);
                logger.warn("Index fraud_flag: {}", e.getMessage());
            }

            try {
                Object result2 = mainG.call("aerospike.graph.admin.index.create")
                        .with("element_type", "vertex")
                        .with("property_key", "~label")
                        .next();

                Map<String, Object> indexResult = new HashMap<>();
                indexResult.put("index", "vertex_label");
                indexResult.put("status", "created");
                indexResult.put("result", result2);
                results.add(indexResult);
                logger.info("Created index: vertex_label");
            } catch (Exception e) {
                Map<String, Object> indexResult = new HashMap<>();
                indexResult.put("index", "vertex_label");
                indexResult.put("status", "error");
                indexResult.put("error", e.getMessage());
                results.add(indexResult);
            }

            try {
                Object result3 = mainG.call("aerospike.graph.admin.index.create")
                        .with("element_type", "vertex")
                        .with("property_key", "account_id")
                        .next();

                Map<String, Object> indexResult = new HashMap<>();
                indexResult.put("index", "account_id");
                indexResult.put("status", "created");
                indexResult.put("result", result3);
                results.add(indexResult);
                logger.info("Created index: account_id");
            } catch (Exception e) {
                Map<String, Object> indexResult = new HashMap<>();
                indexResult.put("index", "account_id");
                indexResult.put("status", "error");
                indexResult.put("error", e.getMessage());
                results.add(indexResult);
            }

            long successful = results.stream()
                    .filter(r -> "created".equals(r.get("status")))
                    .count();

            Map<String, Object> response = new HashMap<>();
            response.put("status", "completed");
            response.put("results", results);
            response.put("total_indexes", results.size());
            response.put("successful", successful);
            return response;

        } catch (Exception e) {
            logger.error("Error creating fraud detection indexes: {}", e.getMessage());
            Map<String, Object> response = new HashMap<>();
            response.put("error", e.getMessage());
            response.put("status", "error");
            return response;
        }
    }

    public void printSummary() {
        final Object summary = mainG.call("aerospike.graph.admin.metadata.summary").next();
        logger.info("Graph summary: {}", summary);
    }
}