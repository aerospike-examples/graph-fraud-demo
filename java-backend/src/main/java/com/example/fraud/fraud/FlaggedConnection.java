package com.example.fraud.fraud;

public record FlaggedConnection(String accountId,
                                String role,
                                int score) {

}
