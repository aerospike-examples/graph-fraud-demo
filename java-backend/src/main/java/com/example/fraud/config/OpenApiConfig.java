package com.example.fraud.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI fraudDetectionOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Fraud Detection API")
                        .description("Backend API for fraud detection system with graph database")
                        .version("1.0.0")
                        .license(new License()
                                .name("MIT")
                                .url("https://opensource.org/licenses/MIT")));
    }

    @Bean
    public GroupedOpenApi publicApi() {
        return GroupedOpenApi.builder()
                .group("fraud-detection")
                .pathsToMatch("/**")
                .build();
    }
}

