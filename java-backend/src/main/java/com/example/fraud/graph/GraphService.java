package com.example.fraud.graph;

import com.example.fraud.config.GraphProperties;
import com.example.fraud.fraud.PerformanceInfo;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.model.TransactionType;
import com.example.fraud.util.FraudUtil;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.UUID;
import java.util.stream.Collectors;
import org.apache.tinkerpop.gremlin.driver.Cluster;
import org.apache.tinkerpop.gremlin.driver.remote.DriverRemoteConnection;
import org.apache.tinkerpop.gremlin.process.traversal.P;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversal;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.GraphTraversalSource;
import org.apache.tinkerpop.gremlin.process.traversal.dsl.graph.__;
import org.apache.tinkerpop.gremlin.structure.T;
import org.apache.tinkerpop.gremlin.process.traversal.Order;
import org.apache.tinkerpop.gremlin.process.traversal.Scope;
import org.apache.tinkerpop.gremlin.process.traversal.TextP;
import org.apache.tinkerpop.gremlin.structure.T;
import org.apache.tinkerpop.gremlin.structure.Vertex;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.springframework.stereotype.Service;

import static com.example.fraud.util.FraudUtil.capitalizeWords;
import static org.apache.tinkerpop.gremlin.process.traversal.AnonymousTraversalSource.traversal;

@Service
public class GraphService {

    private static final Logger logger = LoggerFactory.getLogger(GraphService.class);
    final private GraphProperties props;
    private Cluster fraudCluster;
    private Cluster mainCluster;
    private GraphTraversalSource fraudG;
    private GraphTraversalSource mainG;

    public GraphService(GraphProperties graphProperties) {
        this.props = graphProperties;
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

        } catch (Exception e) {
            logger.error("Could not connect to Aerospike Graph: {}", e.getMessage());
            logger.error("Graph database connection is required. Please ensure Aerospike Graph is running on port {}",
                    props.gremlinPort());
            throw new RuntimeException("Failed to connect to Aerospike Graph", e);
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
            logger.debug("{} transaction created: {} from {} to {} amount {}",
                    genType, txnId, fromId, toId, amount);
            return new TransactionInfo(true, edgeId, txnId, fromId, toId, amount,
                    new PerformanceInfo(start, Duration.between(start, Instant.now()), true));
        } catch (Exception e) {
            logger.error("Error creating transaction: {}", e.getMessage());
            Map<String, Object> error = new HashMap<>();
            error.put("success", false);
            error.put("error", "Error creating transaction: " + e.getMessage());
            return new TransactionInfo(false, null, null, null, null, -1,
                    new PerformanceInfo(start, Duration.between(start, Instant.now()), false));
        }
    }

    public TransactionInfo createManualTransaction(String fromId, String toId, double amount,
                                                   TransactionType type, String genType, String location, Instant start) {
            Map<String, Object> accountCheck = mainG.V(fromId, toId)
                    .project("fromExists", "toExists")
                    .by(__.V(fromId).count())
                    .by(__.V(toId).count())
                    .next();

        if (accountCheck.get("fromExists").equals(0)){
            throw new RuntimeException("from vertex in manual transaction not found");
        }
        if (accountCheck.get("toExists").equals(0)){
            throw new RuntimeException("to vertex in manual transaction not found");
        }
        if (Objects.equals(fromId, toId)) {
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

        return new TransactionInfo(true, edgeId, txnId, fromId, toId, amount,
                new PerformanceInfo(start, Duration.between(start, Instant.now()), true));
    }

    public Map<String, Object> search(String type,
                                      int page,
                                      Integer pageSize,
                                      String orderBy,
                                      String order,
                                      String query) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                throw new IllegalStateException("Graph client not available. Cannot get search results.");
            }

            final int ps = (pageSize == null || pageSize <= 0) ? Integer.MAX_VALUE : pageSize;
            final int startIdx = Math.max(0, (page - 1) * ps);
            final int endIdx = (pageSize == null || pageSize <= 0) ? Integer.MAX_VALUE : startIdx + ps;

            GraphTraversal.Admin<?, ?> base = "user".equalsIgnoreCase(type)
                    ? g.V().hasLabel("user").asAdmin()
                    : g.E().hasLabel("TRANSACTS").asAdmin();

            if (query != null && !query.isBlank()) {
                String qTitle = capitalizeWords(query);
                String qUpper = query.toUpperCase(Locale.ROOT);
                String qLower = query.toLowerCase(Locale.ROOT);

                if ("user".equalsIgnoreCase(type)) {
                    base = ((GraphTraversal<?, ?>) base).or(
                            __.has("name", TextP.containing(qTitle)),
                            __.hasId(TextP.containing(qUpper)),
                            __.has("email", TextP.containing(qLower)),
                            __.has("location", TextP.containing(qTitle))
                    ).asAdmin();
                } else {
                    base = ((GraphTraversal<?, ?>) base).or(
                            __.inV().hasId(TextP.containing(qUpper)),
                            __.outV().hasId(TextP.containing(qUpper)),
                            __.has("txn_id", TextP.containing(qUpper)),
                            __.has("location", TextP.containing(qTitle))
                    ).asAdmin();
                }
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> packed = ((GraphTraversal<?, ?>) base)
                    .elementMap()
                    .order()
                    .by(orderBy, "asc".equalsIgnoreCase(order) ? Order.asc : Order.desc)
                    .fold()
                    .project("total", "results")
                    .by(__.count(Scope.local))
                    .by(__.unfold().range(startIdx, endIdx).fold())
                    .next();

            @SuppressWarnings("unchecked")
            List<Map<Object, Object>> results = (List<Map<Object, Object>>) packed.getOrDefault("results", List.of());
            List<Map<String, Object>> normalized = new ArrayList<>(results.size());
            for (Map<Object, Object> m : results) {
                Map<String, Object> row = new LinkedHashMap<>();
                for (Map.Entry<Object, Object> e : m.entrySet()) {
                    if (T.id.equals(e.getKey())) {
                        row.put("id", e.getValue());
                    } else if (!T.label.equals(e.getKey())) {
                        row.put(String.valueOf(e.getKey()), e.getValue());
                    }
                }
                normalized.add(row);
            }

            int total = ((Number) packed.getOrDefault("total", 0)).intValue();
            int totalPages = (ps == Integer.MAX_VALUE) ? 1 : ((total + ps - 1) / ps);

            Map<String, Object> out = new LinkedHashMap<>();
            out.put("results", normalized);
            out.put("total", total);
            out.put("page", page);
            out.put("page_size", (pageSize == null ? 0 : pageSize));
            out.put("total_pages", totalPages);
            return out;

        } catch (Exception e) {
            logger.error("Error getting search results", e);
            return Map.of(
                    "results", List.of(),
                    "total", 0,
                    "page", page,
                    "page_size", (pageSize == null ? 0 : pageSize),
                    "total_pages", 0
            );
        }
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
                String riskLevel = (riskScore < 25) ? "LOW"
                        : (riskScore < 50) ? "MEDIUM"
                        : (riskScore < 75) ? "HIGH"
                        : "CRITICAL";
                userSummary.put("risk_level", riskLevel);
            }

            return userSummary;

        } catch (Exception e) {
            logger.error("Error getting user summary", e);
            return null;
        }
    }

    public List<Map<String, Object>> getUserAccounts(String userId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                logger.error("No graph client available");
                return null;
            }

            long userCount = g.V(userId).count().next();
            if (userCount == 0) {
                return null;
            }

            @SuppressWarnings("unchecked")
            List<Map<Object, Object>> accounts = (List<Map<Object, Object>>) (List<?>) 
                    g.V(userId).out("OWNS").elementMap().toList();

            List<Map<String, Object>> normalized = new ArrayList<>(accounts.size());
            for (Map<Object, Object> acc : accounts) {
                Map<String, Object> row = new LinkedHashMap<>();
                for (Map.Entry<Object, Object> e : acc.entrySet()) {
                    if (T.id.equals(e.getKey())) {
                        row.put("id", e.getValue());
                    } else if (!T.label.equals(e.getKey())) {
                        row.put(String.valueOf(e.getKey()), e.getValue());
                    }
                }
                normalized.add(row);
            }

            return normalized;

        } catch (Exception e) {
            logger.error("Error getting user accounts for user {}", userId, e);
            return null;
        }
    }

    public List<Map<String, Object>> getUserDevices(String userId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                logger.error("No graph client available");
                return null;
            }

            long userCount = g.V(userId).count().next();
            if (userCount == 0) {
                return null;
            }

            @SuppressWarnings("unchecked")
            List<Map<Object, Object>> devices = (List<Map<Object, Object>>) (List<?>) 
                    g.V(userId).out("USES").elementMap().toList();

            List<Map<String, Object>> normalized = new ArrayList<>(devices.size());
            for (Map<Object, Object> dev : devices) {
                Map<String, Object> row = new LinkedHashMap<>();
                for (Map.Entry<Object, Object> e : dev.entrySet()) {
                    if (T.id.equals(e.getKey())) {
                        row.put("id", e.getValue());
                    } else if (!T.label.equals(e.getKey())) {
                        row.put(String.valueOf(e.getKey()), e.getValue());
                    }
                }
                normalized.add(row);
            }

            return normalized;

        } catch (Exception e) {
            logger.error("Error getting user devices for user {}", userId, e);
            return null;
        }
    }

    public Map<String, Object> getUserTransactions(String userId, int page, int pageSize) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                logger.error("No graph client available");
                return null;
            }

            long userCount = g.V(userId).count().next();
            if (userCount == 0) {
                return null;
            }

            int startIdx = Math.max(0, (page - 1) * pageSize);
            int endIdx = startIdx + pageSize;

            @SuppressWarnings("unchecked")
            Map<String, Object> packed = g.V(userId)
                    .out("OWNS")
                    .bothE("TRANSACTS")
                    .order().by("timestamp", Order.desc)
                    .fold()
                    .project("total", "transactions")
                    .by(__.count(Scope.local))
                    .by(__.unfold().range(startIdx, endIdx)
                            .project("id", "amount", "currency", "timestamp", "location", "status", "type", "from_id", "to_id", "fraud_score", "is_fraud")
                            .by(__.values("txn_id"))
                            .by(__.values("amount"))
                            .by(__.values("currency"))
                            .by(__.values("timestamp"))
                            .by(__.values("location"))
                            .by(__.values("status"))
                            .by(__.values("type"))
                            .by(__.outV().id())
                            .by(__.inV().id())
                            .by(__.coalesce(__.values("fraud_score"), __.constant(0.0)))
                            .by(__.coalesce(__.values("is_fraud"), __.constant(false)))
                            .fold())
                    .next();

            int total = ((Number) packed.getOrDefault("total", 0)).intValue();
            int totalPages = (total + pageSize - 1) / pageSize;

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("transactions", packed.get("transactions"));
            result.put("total", total);
            result.put("page", page);
            result.put("page_size", pageSize);
            result.put("total_pages", totalPages);

            return result;

        } catch (Exception e) {
            logger.error("Error getting user transactions for user {}", userId, e);
            return null;
        }
    }

    public List<Map<String, Object>> getUserConnectedDevices(String userId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                logger.error("No graph client available");
                return List.of();
            }

            @SuppressWarnings("unchecked")
            List<Map<Object, Object>> connectedUsers = (List<Map<Object, Object>>) (List<?>) 
                    g.V(userId)
                            .out("USES")
                            .in("USES")
                            .where(__.not(__.hasId(userId)))
                            .dedup()
                            .project("user_id", "name", "shared_devices")
                            .by(__.id())
                            .by(__.values("name"))
                            .by(__.out("USES")
                                    .where(__.in("USES").hasId(userId))
                                    .id()
                                    .fold())
                            .toList();

            List<Map<String, Object>> normalized = new ArrayList<>(connectedUsers.size());
            for (Map<Object, Object> user : connectedUsers) {
                Map<String, Object> row = new LinkedHashMap<>();
                for (Map.Entry<Object, Object> e : user.entrySet()) {
                    row.put(String.valueOf(e.getKey()), e.getValue());
                }
                normalized.add(row);
            }

            return normalized;

        } catch (Exception e) {
            logger.error("Error getting connected device users for user {}", userId, e);
            return List.of();
        }
    }

    public Map<String, Object> getFlaggedTransactionsPaginated(int page, int pageSize) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) {
                throw new IllegalStateException("Graph client not available");
            }

            List<Vertex> flagged = g.V().hasLabel("transaction").has("fraud_status").toList();

            int startIdx = Math.max(0, (page - 1) * pageSize);
            int endIdx = Math.min(flagged.size(), startIdx + pageSize);
            if (startIdx >= flagged.size()) {
                return Map.of(
                        "transactions", List.of(),
                        "total", flagged.size(),
                        "page", page,
                        "page_size", pageSize,
                        "total_pages", (flagged.size() + pageSize - 1) / pageSize
                );
            }

            List<Map<String, Object>> txns = new ArrayList<>(endIdx - startIdx);

            for (int i = startIdx; i < endIdx; i++) {
                Vertex txV = flagged.get(i);

                Map<String, Object> txProps = FraudUtil.flattenValueMapGeneric(
                        g.V(txV).valueMap().next()
                );

                String senderId = "Unknown";
                try {
                    List<Vertex> senders = g.V(txV).in("TRANSFERS_TO").toList();
                    if (!senders.isEmpty()) {
                        Map<String, Object> senderProps = FraudUtil.flattenValueMapGeneric(
                                g.V(senders.get(0)).valueMap().next()
                        );
                        senderId = String.valueOf(senderProps.getOrDefault("account_id", "Unknown"));
                    }
                } catch (Exception ex) {
                    logger.debug("Error getting sender account", ex);
                }

                String receiverId = "Unknown";
                try {
                    List<Vertex> receivers = g.V(txV).out("TRANSFERS_FROM").toList();
                    if (!receivers.isEmpty()) {
                        Map<String, Object> receiverProps = FraudUtil.flattenValueMapGeneric(
                                g.V(receivers.get(0)).valueMap().next()
                        );
                        receiverId = String.valueOf(receiverProps.getOrDefault("account_id", "Unknown"));
                    }
                } catch (Exception ex) {
                    logger.debug("Error getting receiver account", ex);
                }

                double fraudScore = (double) FraudUtil.getPropertyValue(txV, "fraud_score", 0.0);
                String fraudStatus = FraudUtil.getPropertyValue(txV, "fraud_status", "clean").toString();
                String fraudReason = FraudUtil.getPropertyValue(txV, "reason", "").toString();

                Map<String, Object> row = new LinkedHashMap<>();
                row.put("id", txProps.getOrDefault("transaction_id", ""));
                row.put("sender_id", senderId);
                row.put("receiver_id", receiverId);
                row.put("amount", txProps.getOrDefault("amount", 0.0));
                row.put("currency", "INR");
                row.put("timestamp", txProps.getOrDefault("timestamp", ""));
                row.put("location", txProps.getOrDefault("location", "Unknown"));
                row.put("status", txProps.getOrDefault("status", "completed"));
                row.put("fraud_score", fraudScore);
                row.put("transaction_type", txProps.getOrDefault("type", "transfer"));
                row.put("is_fraud", fraudScore >= 75.0);
                row.put("fraud_status", fraudStatus);
                row.put("fraud_reason", fraudReason);
                row.put("device_id", null);

                txns.add(row);
            }

            int total = flagged.size();
            int totalPages = (total + pageSize - 1) / pageSize;
            return Map.of(
                    "transactions", txns,
                    "total", total,
                    "page", page,
                    "page_size", pageSize,
                    "total_pages", totalPages
            );

        } catch (Exception e) {
            logger.error("Error getting flagged transactions", e);
            return Map.of(
                    "transactions", List.of(),
                    "total", 0,
                    "page", page,
                    "page_size", pageSize,
                    "total_pages", 0
            );
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

    public List<Map<String, Object>> getFlaggedAccounts() {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) throw new IllegalStateException("Graph client not available");

            List<Vertex> accounts = g.V().hasLabel("account").has("fraud_flag", true).toList();

            List<Map<String, Object>> flagged = new ArrayList<>(accounts.size());
            for (Vertex v : accounts) {
                Map<Object, Object> vm = g.V(v).valueMap().next();
                Map<String, Object> acc = FraudUtil.flattenValueMapGeneric(vm);

                Map<String, Object> row = new LinkedHashMap<>();
                row.put("account_id", acc.getOrDefault("account_id", ""));
                row.put("type", acc.getOrDefault("type", ""));
                row.put("balance", acc.getOrDefault("balance", 0.0));
                row.put("flag_reason", acc.getOrDefault("flagReason", ""));
                row.put("flag_timestamp", acc.getOrDefault("flagTimestamp", ""));
                row.put("status", acc.getOrDefault("status", "active"));

                flagged.add(row);
            }
            return flagged;

        } catch (Exception e) {
            logger.error("Error getting flagged accounts", e);
            return List.of();
        }
    }

    public boolean flagAccount(String accountId, String reason) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) throw new IllegalStateException("Graph client not available");

            List<Vertex> accounts = g.V().hasLabel("account").has("account_id", accountId).toList();
            if (accounts.isEmpty()) return false;

            g.V(accounts.get(0))
                    .property("fraud_flag", true)
                    .property("flagReason", reason)
                    .property("flagTimestamp", Instant.now().toString())
                    .iterate();

            logger.info("Account {} flagged as fraudulent: {}", accountId, reason);
            return true;

        } catch (Exception e) {
            logger.error("Error flagging account {}", accountId, e);
            return false;
        }
    }

    public boolean unflagAccount(String accountId) {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) throw new IllegalStateException("Graph client not available");

            List<Vertex> accounts = g.V().hasLabel("account").has("account_id", accountId).toList();
            if (accounts.isEmpty()) return false;

            g.V(accounts.get(0))
                    .property("fraud_flag", false)
                    .property("unflagTimestamp", Instant.now().toString())
                    .iterate();

            logger.info("Account {} unflagged", accountId);
            return true;

        } catch (Exception e) {
            logger.error("Error unflagging account {}", accountId, e);
            return false;
        }
    }

    public List<Map<String, Object>> getAllAccounts() {
        try {
            GraphTraversalSource g = getMainClient();
            if (g == null) return List.of();

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> accounts = (List<Map<String, Object>>) (List<?>)
                    g.V().hasLabel("account")
                            .project("account_id", "account_type")
                            .by(__.id())
                            .by("type")
                            .toList();

            logger.info("Found {} account vertices", accounts.size());
            return accounts;

        } catch (Exception e) {
            logger.error("Error getting all accounts", e);
            return List.of();
        }
    }

    public List<Object> getAccountIds() {

        return mainG.V()
                .hasLabel("account")
                .id()
                .toList();
    }

    public void seedSampleData() {
        mainG.V().drop().iterate();
        String verticesPath = "/data/vertices";
        String edgesPath = "/data/edges";

        logger.info("Bulk load Starting");
        mainG.with("evaluationTimeout", 20000)
                .call("aerospike.graphloader.admin.bulk-load.load")
                .with("aerospike.graphloader.vertices", verticesPath)
                .with("aerospike.graphloader.edges", edgesPath)
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
