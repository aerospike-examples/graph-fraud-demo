package com.example.fraud.generator;

import java.time.Instant;

public record GeneratorStatus (Boolean running, Integer generationRate, Instant startTime){
}
