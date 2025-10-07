package com.example.fraud.cli;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.generator.GeneratorService;
import com.example.fraud.graph.GraphService;
import com.example.fraud.monitor.PerformanceMonitor;
import com.example.fraud.util.Util;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;


import java.io.Console;
import java.util.Locale;
import java.util.Map;
import java.util.Scanner;
import java.util.concurrent.atomic.AtomicBoolean;

@Component
public class FraudCLI implements CommandLineRunner {

    private static final String[]  HOSTS = {"127.0.0.1"};
    private static final int PORT = 8182;
    private static final int TRANSACTION_WORKER_POOL_SIZE = 128;
    private static final int TRANSACTION_WORKER_MAX_POOL_SIZE = 128;
    private static final int FRAUD_POOL_SIZE = 128;
    private static final int FRAUD_MAX_POOL_SIZE = 128;
    private static final int FRAUD_CONNECTION_POOL_WORKERS = 64;
    private static final int FRAUD_CONNECTION_MAX_IN_PROCESS_PER_CONNECTION = 64;
    private static final int MAIN_CONNECTION_POOL_WORKERS = 64;
    private static final int MAIN_CONNECTION_MAX_IN_PROCESS_PER_CONNECTION = 64;

    private static final AtomicBoolean generatorRunning = new AtomicBoolean(false);
    GraphService graphService;
    GeneratorService generatorService;
    FraudService fraudService;
    PerformanceMonitor performanceMonitor;

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
        performanceMonitor = new PerformanceMonitor();
        graphService = new GraphService(HOSTS, PORT, FRAUD_CONNECTION_POOL_WORKERS,
                FRAUD_CONNECTION_MAX_IN_PROCESS_PER_CONNECTION,
                MAIN_CONNECTION_POOL_WORKERS, MAIN_CONNECTION_MAX_IN_PROCESS_PER_CONNECTION);
        fraudService = new FraudService(graphService, performanceMonitor,
                FRAUD_POOL_SIZE, FRAUD_MAX_POOL_SIZE);
        generatorService = new GeneratorService(graphService, fraudService, performanceMonitor,
                TRANSACTION_WORKER_POOL_SIZE, TRANSACTION_WORKER_MAX_POOL_SIZE);

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
        final String[] args = parts.length > 1 ? Util.slice(parts, 1) : new String[0];

        switch (cmd) {
            case "help" -> showHelp();
            case "stats" -> showStats();
            case "performance", "perf" -> showPerformance(parseWindow(args));
            case "fraud", "fraud-perf" -> showFraudPerformance(parseWindow(args));
            case "users" -> showUsers();
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
        generatorService.stopGeneration();
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
        boolean success = generatorService.startGeneration(rate);
        if (success) {
            System.out.println("Generator started.");
        } else {
            System.out.println("Generator failed to start.");
        }
    }

    private void showIndexes() {
        try {
            System.out.println("Database Indexes Information");
            System.out.println(graphService.inspectIndexes());
        } catch (Exception e) {
            System.out.println("Error getting index information: " + e.getMessage());
        }
    }

    private void createFraudIndexes() {
        System.out.println("Creating fraud detection indexes...");
        System.out.print(graphService.createFraudDetectionIndexes());
    }

    private void showStats() {
        try {
            Map<String, Object> stats = graphService.getDashboardStats();

            long users = ((Number) stats.get("users")).longValue();
            long txns = ((Number) stats.get("txns")).longValue();
            long accounts = ((Number) stats.get("accounts")).longValue();
            long devices = ((Number) stats.get("devices")).longValue();
            long flagged = ((Number) stats.get("flagged")).longValue();
            double amount = ((Number) stats.get("amount")).doubleValue();
            double fraudRate = ((Number) stats.get("fraud_rate")).doubleValue();
            String health = (String) stats.get("health");

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
                    
                    """, users, txns, accounts, devices, flagged, amount, fraudRate, health);
        } catch (Exception e) {
            System.out.println("Error getting database stats: " + e.getMessage());
        }
    }

    private void showPerformance(int windowMinutes) {
        try {
            Map<String, Object> stats = performanceMonitor.getTransactionStats();

            boolean isRunning = (Boolean) stats.get("is_running");
            double targetTps = ((Number) stats.get("target_tps")).doubleValue();
            double actualTps = ((Number) stats.get("actual_tps")).doubleValue();
            double currentTps = ((Number) stats.get("current_tps")).doubleValue();
            double elapsedTime = ((Number) stats.get("elapsed_time")).doubleValue();

            long totalScheduled = ((Number) stats.get("total_scheduled")).longValue();
            long totalCompleted = ((Number) stats.get("total_completed")).longValue();
            long totalFailed = ((Number) stats.get("total_failed")).longValue();
            int queueSize = ((Number) stats.get("queue_size")).intValue();

            double avgLatency = ((Number) stats.get("avg_latency_ms")).doubleValue();
            double maxLatency = ((Number) stats.get("max_latency_ms")).doubleValue();
            double successRate = ((Number) stats.get("success_rate")).doubleValue();

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
                    isRunning ? "RUNNING" : "STOPPED",
                    targetTps, currentTps, actualTps, elapsedTime,
                    totalScheduled, totalCompleted, totalFailed, queueSize, successRate,
                    avgLatency, maxLatency);
            showFraudPerformance(1);
        } catch (Exception e) {
            System.out.println("Error getting performance stats: " + e.getMessage());
        }
    }

    private void showFraudPerformance(int windowMinutes) {
        try {
            Map<String, Object> allStats = performanceMonitor.getAllStats(windowMinutes);

            @SuppressWarnings("unchecked")
            Map<String, Object> rt1Stats = (Map<String, Object>) allStats.get("rt1");
            @SuppressWarnings("unchecked")
            Map<String, Object> rt2Stats = (Map<String, Object>) allStats.get("rt2");
            @SuppressWarnings("unchecked")
            Map<String, Object> rt3Stats = (Map<String, Object>) allStats.get("rt3");

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
                    ((Number) rt1Stats.get("avg_execution_time")).doubleValue(),
                    ((Number) rt1Stats.get("max_execution_time")).doubleValue(),
                    ((Number) rt1Stats.get("queries_per_second")).doubleValue(),
                    ((Number) rt1Stats.get("success_rate")).doubleValue(),
                    ((Number) rt1Stats.get("total_queries")).intValue(),

                    ((Number) rt2Stats.get("avg_execution_time")).doubleValue(),
                    ((Number) rt2Stats.get("max_execution_time")).doubleValue(),
                    ((Number) rt2Stats.get("queries_per_second")).doubleValue(),
                    ((Number) rt2Stats.get("success_rate")).doubleValue(),
                    ((Number) rt2Stats.get("total_queries")).intValue(),

                    ((Number) rt3Stats.get("avg_execution_time")).doubleValue(),
                    ((Number) rt3Stats.get("max_execution_time")).doubleValue(),
                    ((Number) rt3Stats.get("queries_per_second")).doubleValue(),
                    ((Number) rt3Stats.get("success_rate")).doubleValue(),
                    ((Number) rt3Stats.get("total_queries")).intValue());

        } catch (Exception e) {
            System.out.println("Error getting fraud performance stats: " + e.getMessage());
        }
    }

    private void showUsers() {
        try {
            Map<String, Object> stats = graphService.getUserStats();

            long totalUsers = ((Number) stats.get("total_users")).longValue();
            long lowRisk = ((Number) stats.get("total_low_risk")).longValue();
            long medRisk = ((Number) stats.get("total_med_risk")).longValue();
            long highRisk = ((Number) stats.get("total_high_risk")).longValue();

            System.out.printf("""
                    User Statistics:
                      Total Users:        %,d
                      Low Risk:           %,d
                      Medium Risk:        %,d
                      High Risk:          %,d
                    
                    """, totalUsers, lowRisk, medRisk, highRisk);
        } catch (Exception e) {
            System.out.println("Error getting user stats: " + e.getMessage());
        }
    }

    private void showTransactions() {
        try {
            Map<String, Object> stats = graphService.getTransactionStats();

            long totalTxns = ((Number) stats.get("total_txns")).longValue();
            long blocked = ((Number) stats.get("total_blocked")).longValue();
            long review = ((Number) stats.get("total_review")).longValue();
            long clean = ((Number) stats.get("total_clean")).longValue();

            System.out.printf("""
                    Transaction Statistics:
                      Total Transactions: %,d
                      Blocked:            %,d
                      Under Review:       %,d
                      Clean:              %,d
                    
                    """, totalTxns, blocked, review, clean);
        } catch (Exception e) {
            System.out.println("Error getting transaction stats: " + e.getMessage());
        }
    }

    private void seed() {
        try {
            System.out.println("Seeding sample data (demo)...");
            graphService.seedSampleData();
        } catch (Exception e) {
            System.out.println("Seed failed: " + e.getMessage());
        }
    }

    private void shutdown() {
        try {
            generatorRunning.set(false);
            graphService.shutdown();
            fraudService.shutdown();
            generatorService.shutdown();
            System.out.println("Application shutdown complete");
        } catch (Exception e) {
            System.err.println("Shutdown error: " + e.getMessage());
        }
    }
}