package com.example.fraud;

import com.example.fraud.cli.FraudCLI;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.WebApplicationType;

@SpringBootApplication
public class App {
    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(FraudCLI.class);
        app.setWebApplicationType(WebApplicationType.NONE);
        app.run(args);
    }
}
