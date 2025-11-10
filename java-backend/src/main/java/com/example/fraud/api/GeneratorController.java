package com.example.fraud.api;

import com.example.fraud.generator.GeneratorService;
import com.example.fraud.generator.GeneratorStatus;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
@Tag(name = "Transaction Generation", description = "Control transaction generation and monitoring")
public class GeneratorController {
    private final GeneratorService transactionGenerator;

    public GeneratorController(GeneratorService transactionGenerator) {
        this.transactionGenerator = transactionGenerator;
    }

    @GetMapping("/generate/status")
    @Operation(summary = "Get Generation Status", description = "Get current transaction generation status and statistics")
    @ApiResponse(
        responseCode = "200",
        description = "Successfully retrieved generation status",
        content = @Content(
            mediaType = "application/json",
            schema = @Schema(implementation = GeneratorStatus.class)
        )
    )
    public ResponseEntity<?> status() {
        var status = transactionGenerator.getStatus();
        var successful = transactionGenerator.getSuccessfulTransactions();

        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("running", status.running());
        out.put("generationRate", status.generationRate());
        out.put("startTime", status.startTime());
        out.put("total", successful);
        return ResponseEntity.ok(out);
    }

    @PostMapping("/generate/start")
    @Operation(summary = "Start Generation", description = "Start transaction generation at specified rate")
    @ApiResponses(value = {
        @ApiResponse(
            responseCode = "200",
            description = "Generation started successfully",
            content = @Content(
                mediaType = "application/json",
                examples = @ExampleObject(
                    value = "{\"message\": \"Transaction generation started at 100 transactions/second\", \"status\": \"started\", \"rate\": 100, \"max_rate\": 500}"
                )
            )
        ),
        @ApiResponse(
            responseCode = "400",
            description = "Invalid rate or generation already running",
            content = @Content(
                mediaType = "application/json",
                examples = @ExampleObject(
                    value = "{\"error\": \"Generation rate 1000 exceeds maximum allowed rate of 500\"}"
                )
            )
        )
    })
    public ResponseEntity<?> start(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Generation rate configuration",
                    required = true,
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(
                                    name = "Start Generation",
                                    value = "{\"rate\": 100}",
                                    description = "Rate in transactions per second"
                            )
                    )
            )
            @RequestBody Map<String, Object> body) {
        try {
            int rate = ((Number) body.get("rate")).intValue();
            int max = transactionGenerator.getMaxTransactionRate();

            if (rate > max) {
                return ResponseEntity.badRequest().body(
                        Map.of("error", "Generation rate " + rate + " exceeds maximum allowed rate of " + max)
                );
            }

            boolean ok = transactionGenerator.startGeneration(rate);
            if (!ok) {
                return ResponseEntity.badRequest().body(
                        Map.of("error", "Transaction generation is already running")
                );
            }

            return ResponseEntity.ok(Map.of(
                    "message", "Transaction generation started at " + rate + " transactions/second",
                    "status", "started",
                    "rate", rate,
                    "max_rate", max
            ));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(
                    Map.of("error", "Failed to start generation: " + e.getMessage())
            );
        }
    }

    @PostMapping("/generate/stop")
    @Operation(summary = "Stop Generation", description = "Stop transaction generation")
    @ApiResponses(value = {
        @ApiResponse(
            responseCode = "200",
            description = "Generation stopped successfully",
            content = @Content(
                mediaType = "application/json",
                examples = @ExampleObject(
                    value = "{\"message\": \"Transaction generation stopped\", \"status\": \"stopped\"}"
                )
            )
        ),
        @ApiResponse(
            responseCode = "400",
            description = "Generation not running",
            content = @Content(
                mediaType = "application/json",
                examples = @ExampleObject(
                    value = "{\"error\": \"Transaction generation is not running\"}"
                )
            )
        )
    })
    public ResponseEntity<?> stop() {
        boolean ok = transactionGenerator.stopGeneration();
        if (!ok) {
            return ResponseEntity.badRequest().body(
                    Map.of("error", "Transaction generation is not running")
            );
        }
        return ResponseEntity.ok(Map.of(
                "message", "Transaction generation stopped",
                "status", "stopped"
        ));
    }

    @GetMapping("/transaction-generation/max-rate")
    @Operation(summary = "Get Max Rate", description = "Get maximum allowed transaction generation rate")
    @ApiResponse(
        responseCode = "200",
        description = "Successfully retrieved max rate",
        content = @Content(
            mediaType = "application/json",
            examples = @ExampleObject(
                value = "{\"max_rate\": 500, \"message\": \"Maximum allowed transaction generation rate: 500 transactions/second\"}"
            )
        )
    )
    public ResponseEntity<?> getMaxRate() {
        int max = transactionGenerator.getMaxTransactionRate();
        return ResponseEntity.ok(Map.of(
                "max_rate", max,
                "message", "Maximum allowed transaction generation rate: " + max + " transactions/second"
        ));
    }
}

