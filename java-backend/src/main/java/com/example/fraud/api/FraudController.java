package com.example.fraud.api;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.rules.Rule;
import java.util.List;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/fraud")
public class FraudController {

    private final FraudService fraudService;

    public FraudController(FraudService fraudService) {
        this.fraudService = fraudService;
    }

    @GetMapping("/rules")
    public List<Rule> getMaxRate() {
        List<Rule> rules = fraudService.getFraudRulesList();
        return List.copyOf(rules);
    }

    @PostMapping("/rules/toggle")
    public ResponseEntity<?> toggleRule(@RequestBody Map<String, Object> body) {
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
