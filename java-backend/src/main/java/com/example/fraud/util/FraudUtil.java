package com.example.fraud.util;

import com.example.fraud.model.TransactionType;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

public class FraudUtil {
    final static private TransactionType[] transactionTypes = TransactionType.values();

    private static final List<String> normalLocations = Arrays.asList(
            "New York, New York", "Los Angeles, California", "Chicago, Illinois", "Houston, Texas",
            "Phoenix, Arizona", "Philadelphia, Pennsylvania", "San Antonio, Texas", "San Diego, California",
            "Dallas, Texas", "San Jose, California", "Austin, Texas", "Jacksonville, Florida",
            "Fort Worth, Texas", "Columbus, Ohio", "Charlotte, North Carolina", "San Francisco, California",
            "Indianapolis, Indiana", "Seattle, Washington", "Denver, Colorado", "Washington, District of Columbia",
            "Boston, Massachusetts", "El Paso, Texas", "Nashville, Tennessee", "Detroit, Michigan",
            "Oklahoma City, Oklahoma", "Portland, Oregon", "Las Vegas, Nevada", "Memphis, Tennessee",
            "Louisville, Kentucky", "Baltimore, Maryland", "Milwaukee, Wisconsin", "Albuquerque, New Mexico",
            "Tucson, Arizona", "Fresno, California", "Sacramento, California", "Mesa, Arizona",
            "Kansas City, Missouri", "Atlanta, Georgia", "Long Beach, California", "Colorado Springs, Colorado",
            "Raleigh, North Carolina", "Miami, Florida", "Virginia Beach, Virginia", "Omaha, Nebraska",
            "Oakland, California", "Minneapolis, Minnesota", "Tulsa, Oklahoma", "Arlington, Texas"
    );

    public static String[] slice(String[] arr, int from) {
        String[] out = new String[arr.length - from];
        System.arraycopy(arr, from, out, 0, out.length);
        return out;
    }

    public static TransactionType getRandomTransactionType() {
        return transactionTypes[new Random().nextInt(transactionTypes.length)];
    }

    public static String getRandomLocation() {
        return normalLocations.get(new Random().nextInt(normalLocations.size()));
    }

}