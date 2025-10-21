package com.example.fraud.cli;

import com.example.fraud.util.FraudUtil;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.context.annotation.Profile;

import java.io.Console;
import java.util.Locale;
import java.util.Scanner;
import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.web.client.RestClient;

@Profile("cli")
@Component
public class FraudCLI implements CommandLineRunner {

    private static final AtomicBoolean generatorRunning = new AtomicBoolean(false);
    private final ServiceOrchestrator orchestrator;
    private final RestClient http;
    private final ObjectMapper mapper = new ObjectMapper();

    public FraudCLI(ServiceOrchestrator orchestrator, RestClient http) {
        this.orchestrator = orchestrator;
        this.http = http;
    }

    private static void showHelp() {
        System.out.println("""
                Available Commands:
                  help                 - Show this help message
                  stats                - Show database statistics
                  transactions, txns   - Show transaction statistics
                  indexes              - Show database indexes information
                  create-fraud-index   - Create Fraud App indexes
                  seed                 - Bulk load users from data/graph_csv (demo)
                  clear-txns           - Clear all transactions from the graph and re-seed
                  start <tps>          - Start generator at specified TPS
                  stop                 - Stop transaction generator
                  status               - Show generator status
                  threads [opts]       - Show JVM thread status. Options:
                                                        --stacks (include stack traces)
                                                        --sort cpu|name|id
                                                        --state RUNNABLE|BLOCKED|WAITING|TIMED_WAITING|NEW|TERMINATED
                  quit, exit           - Exit application
                """);
    }

    private static void printRowHeader() {
        System.out.printf("%-58s %8s %12s %12s %10s %8s %8s %12s%n", "Category", "QPS", "Success", "Failure", "Avg", "Min", "Max", "Elapsed");
        System.out.printf("%-58s %8s %12s %12s %10s %8s %8s %12s%n", repeat('-', 58), repeat('-', 8), repeat('-', 12), repeat('-', 12), repeat('-', 10), repeat('-', 8), repeat('-', 8), repeat('-', 12));
    }

    private static void printRow(String name, double qps, long succ, long fail, double avg, double min, double max, long elapsedSec) {
        System.out.printf("%-58.58s     %.2f %12d %12d       %.2f     %.2f      %.2f %12s%n", name, qps, succ, fail, avg, min, max, human(elapsedSec));
    }

    private static String repeat(char c, int n) {
        char[] arr = new char[n];
        Arrays.fill(arr, c);
        return new String(arr);
    }

    private static String human(long seconds) {
        long d = TimeUnit.SECONDS.toDays(seconds);
        long h = TimeUnit.SECONDS.toHours(seconds) % 24;
        long m = TimeUnit.SECONDS.toMinutes(seconds) % 60;
        long s = seconds % 60;
        if (d > 0) return String.format("%dd %02dh", d, h);
        if (h > 0) return String.format("%dh %02dm", h, m);
        if (m > 0) return String.format("%dm %02ds", m, s);
        return s + "s";
    }

    private static String localTime(String iso) {
        try {
            Instant i = Instant.parse(iso);
            var z = i.atZone(ZoneId.systemDefault());
            return DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss z").format(z);
        } catch (Exception e) {
            return iso;
        }
    }

    public void run(String... args) {
        Locale.setDefault(Locale.US);

        System.out.println("Initializing Fraud Detection CLI (Java)...");

        final Scanner scanner = new Scanner(System.in);
        while (true) {
            final String status = generatorRunning.get() ? "[RUNNING]" : "[STOPPED]";
            System.out.print(status + " fraud-cli> ");
            String line = null;

            Console console = System.console();
            if (console != null) {
                line = console.readLine();
            } else if (scanner.hasNextLine()) {
                line = scanner.nextLine();
            }

            if (line == null) {
                System.out.println("\nExiting...");
                break;
            }

            line = line.trim();
            if (line.isEmpty()) continue;

            handleCommand(line);
        }
        shutdown();
    }

    private void handleCommand(String commandLine) {
        final String[] parts = commandLine.split("\\s+");
        final String cmd = parts[0].toLowerCase();
        final String[] args = parts.length > 1 ? FraudUtil.slice(parts, 1) : new String[0];
        try {
            switch (cmd) {
                case "help" -> showHelp();
                case "stats" -> showPerfStats();
                case "transactions", "txns" -> showTransactions();
                case "indexes" -> showIndexes();
                case "create-fraud-index" -> createFraudIndexes();
                case "seed", "clear-txns" -> {
                    seed();
                    System.out.println("Transactions cleared!");
                }
                case "threads" -> showThreads(args);
                case "status" -> generatorStatus();
                case "start" -> startGenerator(args);
                case "stop" -> stopGenerator();
                case "quit", "exit" -> {
                    System.out.println("Exiting...");
                    shutdown();
                    System.exit(0);
                }
                default -> System.out.println("Unknown command: " + cmd + ". Type 'help' for available commands.");
            }
        } catch (Exception e) {
            System.out.println(e.getMessage());
        }

    }

    private void generatorStatus() {
        try {
            String json = http.get().uri(uri -> uri.path("/generate/status").build()).retrieve().body(String.class);
            System.out.println("Generator Status: \n" + json);
            generatorRunning.compareAndSet(true, false);
        } catch (Exception e) {
            System.out.println("Error getting status: " + e.getMessage());
        }
    }

    private void seed() {
        try {
            http.post().uri(uri -> uri.path("/bulk-load").build()).retrieve().toBodilessEntity();
            System.out.println("Bulk load seeded!");
            generatorRunning.compareAndSet(true, false);
        } catch (Exception e) {
            System.out.println("Error seeding data: " + e.getMessage());
        }
    }

    private void stopGenerator() {
        try {
            String json = http.post().uri(uri -> uri.path("/generate/stop").build()).retrieve().body(String.class);
            JsonNode root = mapper.readTree(json);
            if (root.has("status") && "stopped".equals(root.get("status").asText())) {
                System.out.println("Generator stopped!");
                generatorRunning.compareAndSet(true, false);
            } else {
                System.out.println("Failed to stop generator");
            }
        } catch (Exception e) {
            System.out.println("Error stopping generator: " + e.getMessage());
        }
    }

    private void startGenerator(String[] args) {
        if (args.length != 1) {
            System.out.println("""
                    [ERROR] Invalid Arguements. Expected single int after command line.\
                    
                    \tPlease input a tps.\s
                    \texample: start 200""");
            return;
        }
        try {
            int rate = Integer.parseInt(args[0]);
            String requestBody = String.format("{\"rate\": %d, \"start\": \"now\"}", rate);
            
            String json = http.post()
                    .uri(uri -> uri.path("/generate/start").build())
                    .header("Content-Type", "application/json")
                    .body(requestBody)
                    .retrieve()
                    .body(String.class);

            JsonNode root = mapper.readTree(json);
            if (root.has("status") && "started".equals(root.get("status").asText())) {
                System.out.println("Generator started at " + root.get("rate").asInt() + " TPS.");
                generatorRunning.compareAndSet(false, true);
            } else if (root.has("error")) {
                System.out.println("Error: " + root.get("error").asText());
            } else {
                System.out.println("Generator failed to start.");
            }
        } catch (Exception e) {
            System.out.println("Error starting generator: " + e.getMessage());
        }
    }

    private void showIndexes() {
        try {
            System.out.println("Database Indexes Information");
            String json = http.get().uri(uri -> uri.path("/admin/indexes").build()).retrieve().body(String.class);

            JsonNode root = mapper.readTree(json);

            System.out.println("Indexes information successfully retreived");
            List<String> indexes = new ArrayList<>();
            root.get("index_list").forEach(n -> indexes.add(n.asText()));
            System.out.println("\nGraph Indexes (" + indexes.size() + "):");
            for (int i = 0; i < indexes.size(); i++) {
                System.out.printf("  %2d. %s%n", i + 1, indexes.get(i));
            }
        } catch (Exception e) {
            System.out.println("Error getting index information: " + e.getMessage());
        }
    }

    private void createFraudIndexes() {
        System.out.println("Creating fraud detection indexes...");
        try {
            String json = http.post().uri(uri -> uri.path("/admin/indexes/create-transaction-indexes").build()).retrieve().body(String.class);
            JsonNode root = mapper.readTree(json);

            System.out.println("Fraud indexes created successfully.");
        } catch (JsonProcessingException e) {
            System.out.println("Error creating indexes: " + e.getMessage());
        }
    }

    private void showTransactions() {
        try {
            TransactionStatResponse stats = http.get().uri(uri -> uri.path("/transactions/stats").build()).retrieve().body(TransactionStatResponse.class);
            if (stats == null) {
                System.out.println("Error getting transaction stats");
            }
            System.out.printf("""
                    Transaction Statistics:
                      Total Transactions: %,d
                      Blocked:            %,d
                      Under Review:       %,d
                      Clean:              %,d
                    
                    """, stats.total_txns(), stats.total_blocked(), stats.total_review(), stats.total_clean());
        } catch (Exception e) {
            System.out.println("Error getting transaction stats: " + e.getMessage());
        }
    }

    private void showPerfStats() {
        try {
            String json = http.get().uri(uri -> uri.path("/performance/stats").queryParam("time_window", 5).build()).retrieve().body(String.class);

            JsonNode root = mapper.readTree(json);
            if (root == null || !root.has("performance_stats")) {
                System.out.println("Unable to inspect statistics.");
                return;
            }

            int windowMin = root.path("time_window_minutes").asInt();
            JsonNode p = root.path("performance_stats");
            boolean running = p.path("is_running").asBoolean();
            String tsIso = p.path("timestamp").asText(null);

            JsonNode txn = p.path("transaction_stats");

            List<Map.Entry<String, JsonNode>> categories = new ArrayList<>();
            for (Map.Entry<String, JsonNode> e : p.properties()) {
                String k = e.getKey();
                JsonNode v = e.getValue();
                if (v.isObject() && !k.equals("transaction_stats") && !k.equals("timestamp") && !k.equals("is_running")) {
                    categories.add(Map.entry(k, v));
                }
            }
            categories.sort(Comparator.comparing(Map.Entry::getKey));

            System.out.println();
            System.out.printf("Performance (last %d min) — %s%n", windowMin, tsIso == null ? "n/a" : localTime(tsIso));
            System.out.printf("Status: %s%n%n", running ? "RUNNING" : "STOPPED");

            System.out.println("Overall Transactions");
            printRowHeader();
            printRow("TOTAL", txn.path("QPS").asDouble(), txn.path("total_success").asLong(), txn.path("total_failure").asLong(), txn.path("average").asDouble(), txn.path("min").asDouble(), txn.path("max").asDouble(), txn.path("elapsed_time_seconds").asLong());

            if (!categories.isEmpty()) {
                System.out.println();
                System.out.println("By Category");
                printRowHeader();
                for (var entry : categories) {
                    JsonNode v = entry.getValue();
                    printRow(entry.getKey(), v.path("QPS").asDouble(), v.path("total_success").asLong(), v.path("total_failure").asLong(), v.path("average").asDouble(), v.path("min").asDouble(), v.path("max").asDouble(), v.path("elapsed_time_seconds").asLong());
                }
            }
            System.out.println();

        } catch (Exception e) {
            System.out.println("Error getting performance stats: " + e.getMessage());
        }
    }

    private void shutdown() {
        try {
            generatorRunning.set(false);
            orchestrator.runShutdownFLow();
            System.out.println("Application shutdown complete");
        } catch (Exception e) {
            System.err.println("Shutdown error: " + e.getMessage());
        }
    }

    private void showThreads(String[] args) {
        boolean includeStacks = false;
        java.lang.Thread.State filterState = null;
        String sortKey = "cpu"; // cpu|name|id (default cpu)

        for (String a : args) {
            switch (a.toLowerCase(Locale.ROOT)) {
                case "--stacks" -> includeStacks = true;
                case "--sort=name" -> sortKey = "name";
                case "--sort=id" -> sortKey = "id";
                case "--sort=cpu" -> sortKey = "cpu";
                default -> {
                    if (a.startsWith("--state=")) {
                        String s = a.substring("--state=".length());
                        try {
                            filterState = java.lang.Thread.State.valueOf(s);
                        } catch (IllegalArgumentException ex) {
                            System.out.println("Unknown state: " + s + ". Valid: NEW, RUNNABLE, BLOCKED, WAITING, TIMED_WAITING, TERMINATED");
                            return;
                        }
                    }
                }
            }
        }

        var mx = java.lang.management.ManagementFactory.getThreadMXBean();
        boolean cpuSupported = mx.isThreadCpuTimeSupported();
        if (cpuSupported && !mx.isThreadCpuTimeEnabled()) {
            try {
                mx.setThreadCpuTimeEnabled(true);
            } catch (SecurityException ignored) {
            }
        }

        long[] ids = mx.getAllThreadIds();
        // depth=Integer.MAX_VALUE captures full stack if includeStacks
        java.lang.management.ThreadInfo[] infos = includeStacks
                ? mx.getThreadInfo(ids, Integer.MAX_VALUE)
                : mx.getThreadInfo(ids, 1);

        record Row(long id, String name, Thread.State state, boolean daemon,
                   long cpuMs, long userMs, long blocked, long waited) {
        }

        List<Row> rows = new ArrayList<>();
        long daemonCount = 0, nonDaemonCount = 0;

        // Build rows + collect daemon counts
        Map<Long, Thread> live = Thread.getAllStackTraces().keySet().stream()
                .collect(java.util.stream.Collectors.toMap(Thread::getId, t -> t));

        for (java.lang.management.ThreadInfo ti : infos) {
            if (ti == null) continue; // can be null if thread died between calls
            Thread t = live.get(ti.getThreadId());
            boolean daemon = t != null && t.isDaemon();
            if (daemon) daemonCount++;
            else nonDaemonCount++;

            if (filterState != null && ti.getThreadState() != filterState) continue;

            long cpuMs = (cpuSupported ? mx.getThreadCpuTime(ti.getThreadId()) : -1L);
            long usrMs = (cpuSupported ? mx.getThreadUserTime(ti.getThreadId()) : -1L);
            cpuMs = cpuMs < 0 ? -1 : cpuMs / 1_000_000L;
            usrMs = usrMs < 0 ? -1 : usrMs / 1_000_000L;

            rows.add(new Row(
                    ti.getThreadId(),
                    ti.getThreadName(),
                    ti.getThreadState(),
                    daemon,
                    cpuMs,
                    usrMs,
                    ti.getBlockedCount(),
                    ti.getWaitedCount()
            ));
        }

        // Sort
        Comparator<Row> cmp = switch (sortKey) {
            case "name" -> Comparator.comparing(Row::name, String.CASE_INSENSITIVE_ORDER);
            case "id" -> Comparator.comparingLong(Row::id);
            default -> Comparator.<Row>comparingLong(r -> r.cpuMs < 0 ? Long.MIN_VALUE : r.cpuMs).reversed()
                    .thenComparing(Row::name);
        };
        rows.sort(cmp);

        // Print summary
        System.out.printf("Threads: total=%d, daemon=%d, non-daemon=%d, cpuTimeSupported=%s%n",
                rows.size(), daemonCount, nonDaemonCount, cpuSupported);

        // Header
        System.out.printf("%-6s %-40.40s %-14s %-6s %10s %10s %10s %10s%n",
                "ID", "Name", "State", "Daemon", "CPU(ms)", "User(ms)", "Blocked", "Waited");
        System.out.printf("%-6s %-40.40s %-14s %-6s %10s %10s %10s %10s%n",
                repeat('-', 6), repeat('-', 40), repeat('-', 14), repeat('-', 6),
                repeat('-', 10), repeat('-', 10), repeat('-', 10), repeat('-', 10));

        for (Row r : rows) {
            System.out.printf("%6d %-40.40s %-14s %-6s %10s %10s %10d %10d%n",
                    r.id(), r.name(), r.state(), r.daemon() ? "yes" : "no",
                    r.cpuMs() >= 0 ? Long.toString(r.cpuMs()) : "n/a",
                    r.userMs() >= 0 ? Long.toString(r.userMs()) : "n/a",
                    r.blocked(), r.waited());

            if (includeStacks) {
                java.lang.management.ThreadInfo ti = mx.getThreadInfo(r.id(), Integer.MAX_VALUE);
                if (ti != null) {
                    for (StackTraceElement ste : ti.getStackTrace()) {
                        System.out.println("    at " + ste);
                    }
                    var loc = ti.getLockInfo();
                    if (loc != null) {
                        System.out.println("    on lock " + loc);
                    }
                    var owners = ti.getLockedMonitors();
                    if (owners != null && owners.length > 0) {
                        System.out.println("    locked monitors:");
                        for (var m : owners) System.out.println("      * " + m);
                    }
                    var syncs = ti.getLockedSynchronizers();
                    if (syncs != null && syncs.length > 0) {
                        System.out.println("    locked synchronizers:");
                        for (var s : syncs) System.out.println("      * " + s);
                    }
                    System.out.println();
                }
            }
        }
    }

    private JsonNode readJson(String s) {
        try {
            return mapper.readTree(s);
        } catch (Exception e) {
            throw new RuntimeException("Bad JSON from server", e);
        }
    }

    record TransactionStatResponse(Long total_txns, Long total_blocked, Long total_review, Long total_clean) {
    }
}
