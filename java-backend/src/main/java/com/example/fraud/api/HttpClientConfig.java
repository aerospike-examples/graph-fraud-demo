package com.example.fraud.api;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class HttpClientConfig {

    @Bean
    RestClient restClient(RestClient.Builder builder,
                          @Value("${app.api-base-url:http://localhost:${server.port}/api}") String baseUrl) {
        return builder.baseUrl(baseUrl).build();
    }
}
