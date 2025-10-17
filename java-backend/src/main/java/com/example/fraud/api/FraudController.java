package com.example.fraud.api;

import com.example.fraud.fraud.FraudService;
import com.example.fraud.fraud.TransactionInfo;
import com.example.fraud.generator.GeneratorService;
import com.example.fraud.graph.GraphService;
import com.example.fraud.model.TransactionType;
import com.example.fraud.rules.Rule;
import com.example.fraud.util.FraudUtil;
import jakarta.validation.constraints.Min;
import java.time.Instant;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/fraud")
public class FraudController {

    private final FraudService fraudService;

    public FraudController(FraudService fraudService) {
        this.fraudService = fraudService;
    }

    // GET /fraud/rules
    @GetMapping("/rules")
    public List<Rule> getMaxRate() {
        List<Rule> rules = fraudService.getFraudRulesList();
        return List.copyOf(rules);
    }
}
