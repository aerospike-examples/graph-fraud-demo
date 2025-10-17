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


import java.io.Console;
import java.util.Locale;
import java.util.Scanner;
import java.util.concurrent.atomic.AtomicBoolean;
import org.springframework.web.client.RestClient;

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
                  quit, exit           - Exit application
                """);
    }

    private static int parseWindow(String[] args) {
        int w = 1;
        if (args.length > 0) {
            try {
                w = Integer.parseInt(args[0]);
            } catch (NumberFormatException ignored) {
            }
        }
        if (w != 1 && w != 5 && w != 10) {
            System.out.println("Time window must be 1, 5, or 10. Using 1.");
            w = 1;
        }
        return w;
    }

    private static void printRowHeader() {
        System.out.printf("%-58s %8s %12s %12s %10s %8s %8s %12s%n",
                "Category", "QPS", "Success", "Failure", "Avg", "Min", "Max", "Elapsed");
        System.out.printf("%-58s %8s %12s %12s %10s %8s %8s %12s%n",
                repeat('-', 58), repeat('-', 8), repeat('-', 12), repeat('-', 12),
                repeat('-', 10), repeat('-', 8), repeat('-', 8), repeat('-', 12));
    }

    private static void printRow(String name, double qps, long succ, long fail, double avg, double min, double max,
                                 long elapsedSec) {
        System.out.printf("%-58.58s     %.2f %12d %12d       %.2f     %.2f      %.2f %12s%n",
                name, qps, succ, fail, avg, min, max, human(elapsedSec));
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
            String json = http.get()
                    .uri(uri -> uri.path("/generator/status").build())
                    .retrieve()
                    .body(String.class);
            System.out.println("Generator Status: \n" + json);
            generatorRunning.compareAndSet(true, false);
        } catch (Exception e) {
            System.out.println("Error seeding data: " + e.getMessage());
        }
    }

    private void seed() {
        try {
            String json = http.post()
                    .uri(uri -> uri.path("/bulk-load").build())
                    .retrieve()
                    .body(String.class);
            System.out.println("Bulk load seeded!");
            generatorRunning.compareAndSet(true, false);
        } catch (Exception e) {
            System.out.println("Error seeding data: " + e.getMessage());
        }
    }

    private void stopGenerator() {
        try {
            BasicResponse resp = http.post().uri(uri -> uri.path("/generator/stop").build())
                    .retrieve().body(BasicResponse.class);
            System.out.println("Generator stopped!");
            generatorRunning.compareAndSet(true, false);
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
        int rate = Integer.parseInt(args[0]);

        StartResponse resp = http.post().uri(uri -> uri.path("/generator/start")
                .queryParam("rate", rate).build()).retrieve().body(StartResponse.class);
        boolean ok = resp != null && "started".equalsIgnoreCase(resp.status());
        if (ok) {
            System.out.println("Generator started.");
            generatorRunning.compareAndSet(false, true);
        } else {
            System.out.println("Generator failed to start.");
        }
    }

    private void showIndexes() {
        try {
            System.out.println("Database Indexes Information");
            String json = http.get()
                    .uri(uri -> uri.path("/admin/indexes").build())
                    .retrieve()
                    .body(String.class);

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
            String json = http.get()
                    .uri(uri -> uri.path("/admin/indexes/create-transaction-indexes")
                            .build()).retrieve()
                    .body(String.class);
            JsonNode root = mapper.readTree(json);


            System.out.print("Fraud indexes created successfully.");
        } catch (JsonProcessingException e) {
            System.out.println("Error creating indexes: " + e.getMessage());
        }

    }

    private void showTransactions() {
        try {
            TransactionStatResponse stats = http.get().uri(uri -> uri.path("/transactions/stats")
                    .build()).retrieve().body(TransactionStatResponse.class);
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
            String json = http.get()
                    .uri(uri -> uri.path("/performance/stats").queryParam("time_window", 5).build())
                    .retrieve()
                    .body(String.class);

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
            p.fields().forEachRemaining(e -> {
                String k = e.getKey();
                JsonNode v = e.getValue();
                if (v.isObject() && !k.equals("transaction_stats") && !k.equals("timestamp") && !k.equals("is_running")) {
                    categories.add(Map.entry(k, v));
                }
            });
            categories.sort(Comparator.comparing(Map.Entry::getKey));

            System.out.println();
            System.out.printf("Performance (last %d min) — %s%n", windowMin, tsIso == null ? "n/a" : localTime(tsIso));
            System.out.printf("Status: %s%n%n", running ? "RUNNING" : "STOPPED");

            System.out.println("Overall Transactions");
            printRowHeader();
            printRow("TOTAL",
                    txn.path("QPS").asDouble(),
                    txn.path("total_success").asLong(),
                    txn.path("total_failure").asLong(),
                    txn.path("average").asDouble(),
                    txn.path("min").asDouble(),
                    txn.path("max").asDouble(),
                    txn.path("elapsed_time_seconds").asLong());

            if (!categories.isEmpty()) {
                System.out.println();
                System.out.println("By Category");
                printRowHeader();
                for (var entry : categories) {
                    JsonNode v = entry.getValue();
                    printRow(entry.getKey(),
                            v.path("QPS").asDouble(),
                            v.path("total_success").asLong(),
                            v.path("total_failure").asLong(),
                            v.path("average").asDouble(),
                            v.path("min").asDouble(),
                            v.path("max").asDouble(),
                            v.path("elapsed_time_seconds").asLong());
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

    private JsonNode readJson(String s) {
        try {
            return mapper.readTree(s);
        } catch (Exception e) {
            throw new RuntimeException("Bad JSON from server", e);
        }
    }

    record BasicResponse(String message, String status, Boolean ok) {
    }

    record StartResponse(String message, String status, Integer rate, Integer max_rate) {
    }

    record ShowIndexResponse(String message, String status) {
    }

    record TransactionStatResponse(Long total_txns, Long total_blocked, Long total_review, Long total_clean) {
    }
}