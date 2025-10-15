package com.example.fraud.cli;

import com.example.fraud.util.FraudUtil;
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

    public FraudCLI(ServiceOrchestrator orchestrator, RestClient http) {
        this.orchestrator = orchestrator;
        this.http = http;
    }

    private static void showHelp() {
        System.out.println("""
                Available Commands:
                  help                 - Show this help message
                  stats                - Show database statistics
                  performance, perf [time]   - Show performance metrics (1, 5, or 10 minutes; default 1)
                  fraud, fraud-perf [time]   - Show fraud detection performance
                  users                - Show user statistics
                  transactions, txns   - Show transaction statistics
                  indexes              - Show database indexes information
                  create-fraud-index   - Create Fraud App indexes
                  seed                 - Bulk load users from data/graph_csv (demo)
                  start <tps>          - Start generator at specified TPS
                  stop                 - Stop transaction generator
                  status               - Show generator status
                  clear-txns           - Clear all transactions from the graph (confirmation)
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

        switch (cmd) {
            case "help" -> showHelp();
            case "stats" -> showStats();
            case "performance", "perf" -> showPerformance(parseWindow(args));
            case "fraud", "fraud-perf" -> showFraudPerformance(parseWindow(args));
            case "transactions", "txns" -> showTransactions();
            case "indexes" -> showIndexes();
            case "create-fraud-index" -> createFraudIndexes();
            case "seed", "clear-txns" -> {
                seed();
                System.out.println("Transactions cleared!");
            }
            case "start" -> startGenerator(args);
            case "stop" -> stopGenerator();
            case "quit", "exit" -> {
                System.out.println("Exiting...");
                shutdown();
                System.exit(0);
            }
            default -> System.out.println("Unknown command: " + cmd + ". Type 'help' for available commands.");
        }
    }

    private void stopGenerator() {
        generatorRunning.compareAndSet(true, false);
        BasicResponse resp = http.post().uri(uri -> uri.path("/generator/stop").build())
                .retrieve().body(BasicResponse.class);
        boolean ok = resp != null && resp.ok();
        if (ok) {
            System.out.println("Generator stopped!");
        } else {
            System.out.println("Error stopping generator: " + resp.message());
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
        generatorRunning.compareAndSet(false, true);
        int rate = Integer.parseInt(args[0]);

        StartResponse resp = http.post().uri(uri -> uri.path("/generator/start")
                .queryParam("rate", rate).build()).retrieve().body(StartResponse.class);
        boolean ok = resp != null && "started".equalsIgnoreCase(resp.status());
        if (ok) {
            System.out.println("Generator started.");
        } else {
            System.out.println("Generator failed to start.");
        }
    }

    private void showIndexes() {
        try {
            System.out.println("Database Indexes Information");
            ShowIndexResponse resp = http.post().uri(uri -> uri.path("/admin/indexes")
                    .build()).retrieve().body(ShowIndexResponse.class);

            boolean ok = resp != null && resp.status().equalsIgnoreCase("ok");
            if (!ok) {
                System.out.println("Unable to inspect indexes.");
            } else {
                System.out.println("Indexes information successfully retreived");
            }
            //System.out.println(graphService.inspectIndexes());
        } catch (Exception e) {
            System.out.println("Error getting index information: " + e.getMessage());
        }
    }

    private void createFraudIndexes() {
        System.out.println("Creating fraud detection indexes...");
        BasicResponse resp = http.post().uri(uri -> uri.path("/admin/indexes/create-transaction-indexes")
                .build()).retrieve().body(BasicResponse.class);
        boolean ok = resp != null && resp.ok();
        if (!ok) {
            System.out.println("Fraud indexes were unable to be created.");
        } else {
            System.out.print("Fraud indexes created successfully.");
        }

    }

    private void showStats() {
        try {
            BasicResponse resp = http.post().uri(uri -> uri.path("/performance/stats")
                    .queryParam("time_window", 5).build()).retrieve().body(BasicResponse.class);
            boolean ok = resp != null && resp.ok();
            if (!ok) {
                System.out.println("Unable to inspect statistics.");
                return;
            }
            System.out.println(resp.message());
            System.out.printf("""
                    Database Statistics:
                      Users:              %,d
                      Transactions:       %,d
                      Accounts:           %,d
                      Devices:            %,d
                      Flagged:            %,d
                      Total Amount:       $%,.2f
                      Fraud Rate:         %.1f%%
                      Health:             %s
                    
                    """, 0, 0, 0, 0, 0, 0, 0, "DONT KNOW");
        } catch (Exception e) {
            System.out.println("Error getting database stats: " + e.getMessage());
        }
    }

    private void showPerformance(int windowMinutes) {
        try {
            //Map<String, Object> stats = performanceMonitor.getTransactionStats();

            System.out.printf("""
                            Performance Metrics (%d min window):
                              Status:             %s
                              Target TPS:         %.1f
                              Current TPS:        %.1f
                              Actual TPS:         %.1f
                              Elapsed Time:       %.1fs
                            
                              Scheduled:          %,d
                              Completed:          %,d
                              Failed:             %,d
                              Queue Size:         %d
                              Success Rate:       %.1f%%
                            
                              Avg Latency:        %.1fms
                              Max Latency:        %.1fms
                            
                            """, windowMinutes,
                    "DONT KNOW",
                    0, 0, 0, 0,
                    0, 0, 0, 0, 0,
                    0, 0);
            showFraudPerformance(1);
        } catch (Exception e) {
            System.out.println("Error getting performance stats: " + e.getMessage());
        }
    }

    private void showFraudPerformance(int windowMinutes) {
        try {
            // TODO: Implement for dynamic amount of rules with new
            //Map<String, Object> allStats = performanceMonitor.getAllStats(windowMinutes);
            record ShowUserResponse(Long total_txns, Long total_blocked, Long total_review, Long total_clean) {}
            ShowUserResponse stats = http.post().uri(uri -> uri.path("/generator/start")
                    .build()).retrieve().body(ShowUserResponse.class);
            if (stats == null) {
                System.out.println("Error getting transaction stats");
            }


            System.out.printf("""
                            Fraud Detection Performance (%d min window):
                            
                              RT1 (Account Lookup):
                                Avg Time:          %.2fms
                                Max Time:          %.2fms
                                Queries/sec:       %.2f
                                Success Rate:      %.1f%%
                                Total Queries:     %d
                            
                              RT2 (Network Analysis):
                                Avg Time:          %.2fms
                                Max Time:          %.2fms
                                Queries/sec:       %.2f
                                Success Rate:      %.1f%%
                                Total Queries:     %d
                            
                              RT3 (Pattern Analysis):
                                Avg Time:          %.2fms
                                Max Time:          %.2fms
                                Queries/sec:       %.2f
                                Success Rate:      %.1f%%
                                Total Queries:     %d
                            
                            """, windowMinutes,
                    0,0,0,0,0,
                    0,0,0,0,0,
                    0,0,0,0,0);

        } catch (Exception e) {
            System.out.println("Error getting fraud performance stats: " + e.getMessage());
        }
    }

    private void showTransactions() {
        try {
            TransactionStatResponse stats = http.post().uri(uri -> uri.path("/transactions/stats")
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

    private void seed() {
        try {
            System.out.println("Seeding sample data (demo)...");
            //graphService.seedSampleData();
        } catch (Exception e) {
            System.out.println("Seed failed: " + e.getMessage());
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

    record BasicResponse(String message, String status, Boolean ok) {};
    record StartResponse(String message, String status, Integer rate, Integer max_rate) {}
    record ShowIndexResponse(String message, String status) {};
    record TransactionStatResponse(Long total_txns, Long total_blocked, Long total_review, Long total_clean) {}

}