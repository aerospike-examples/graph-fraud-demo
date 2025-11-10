package com.example.fraud.api;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class ApiDocsController {

    @GetMapping("/docs")
    public String redirectToDocs() {
        return "redirect:/swagger-ui/index.html";
    }

    @GetMapping("/api-docs")
    public String redirectToApiDocs() {
        return "redirect:/swagger-ui/index.html";
    }

    @GetMapping("/swagger-ui")
    public String redirectToSwaggerUi() {
        return "redirect:/swagger-ui/index.html";
    }
}

