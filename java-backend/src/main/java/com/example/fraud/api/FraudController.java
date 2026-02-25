package com.example.fraud.api;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.rules.Rule;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.ExampleObject;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/fraud")
@Tag(name = "Fraud Operations", description = "Operations on fraud rules")
public class FraudController {

    private final FraudService fraudService;

    public FraudController(FraudService fraudService) {
        this.fraudService = fraudService;
    }

    @GetMapping("/rules")
    @ApiResponse(
        responseCode = "200",
        description = "Successfully retrieved fraud rules",
        content = @Content(
            mediaType = "application/json",
            schema = @Schema(implementation = Rule.class)
        )
    )
    public List<Rule> getMaxRate() {
        List<Rule> rules = fraudService.getFraudRulesList();
        return List.copyOf(rules);
    }

    @PostMapping("/rules/toggle")
    @ApiResponses(value = {
        @ApiResponse(
            responseCode = "200",
            description = "Rule successfully toggled",
            content = @Content(
                mediaType = "application/json",
                examples = @ExampleObject(
                    value = "{\"message\": \"Rule 'high-velocity' set to true\", \"name\": \"high-velocity\", \"enabled\": true}"
                )
            )
        ),
        @ApiResponse(
            responseCode = "400",
            description = "Invalid request or rule not found",
            content = @Content(
                mediaType = "application/json",
                examples = @ExampleObject(
                    value = "{\"error\": \"Rule not found: invalid-rule\"}"
                )
            )
        )
    })
    public ResponseEntity<?> toggleRule(
            @io.swagger.v3.oas.annotations.parameters.RequestBody(
                    description = "Rule toggle configuration",
                    required = true,
                    content = @Content(
                            mediaType = "application/json",
                            examples = @ExampleObject(
                                    name = "Toggle Rule",
                                    value = "{\"name\": \"high-velocity\", \"enabled\": true}",
                                    description = "Specify rule name and desired enabled state"
                            )
                    )
            )
            @RequestBody Map<String, Object> body) {
        try {
            String name = String.valueOf(body.get("name"));
            boolean enabled = Boolean.TRUE.equals(body.get("enabled")) || "true".equalsIgnoreCase(String.valueOf(body.get("enabled")));
            boolean ok = fraudService.setRuleEnabled(name, enabled);
            if (!ok) {
                return ResponseEntity.badRequest().body(Map.of("error", "Rule not found: " + name));
            }
            return ResponseEntity.ok(Map.of(
                    "message", "Rule '" + name + "' set to " + enabled,
                    "name", name,
                    "enabled", enabled
            ));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }
}
