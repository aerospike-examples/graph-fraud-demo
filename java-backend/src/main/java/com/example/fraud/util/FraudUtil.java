package com.example.fraud.util;

import com.example.fraud.model.TransactionType;
import java.util.Arrays;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.stream.Collectors;
import org.apache.tinkerpop.gremlin.structure.Vertex;
import org.apache.tinkerpop.gremlin.structure.VertexProperty;

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

    public static String formatElapsed(long seconds) {
        if (seconds >= 3600) return String.format("%.1fh", seconds / 3600.0);
        if (seconds >= 60) return String.format("%.1fm", seconds / 60.0);
        return String.format("%.1fs", (double) seconds);
    }

    public static double bytesToGb(long bytes) {
        return bytes / 1024.0 / 1024.0 / 1024.0;
    }

    public static double computeActualTps(long elapsedSec, long completed) {
        if (elapsedSec <= 0) return 0.0;
        return completed / (double) elapsedSec;
    }

    public static TransactionType getRandomTransactionType() {
        return transactionTypes[new Random().nextInt(transactionTypes.length)];
    }

    public static String getRandomLocation() {
        return normalLocations.get(new Random().nextInt(normalLocations.size()));
    }

    public static String capitalizeWords(String s) {
        if (s == null || s.isBlank()) return s;
        return Arrays.stream(s.split("\\s+"))
                .map(w -> w.isEmpty() ? w : Character.toUpperCase(w.charAt(0)) + w.substring(1))
                .collect(Collectors.joining(" "));
    }

    public static Object getPropertyValue(Vertex v, String propertyName, Object defaultValue) {
        for (Iterator<VertexProperty<Object>> it = v.properties(); it.hasNext(); ) {
            VertexProperty<Object> prop = it.next();
            if (prop.key().equals(propertyName)) {
                return prop.value();
            }
        }
        return defaultValue;
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> flattenValueMapGeneric(Map<Object, Object> valueMap) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<Object, Object> e : valueMap.entrySet()) {
            String key = String.valueOf(e.getKey());
            Object v = e.getValue();
            if (v instanceof List<?> list) {
                // empty list -> null, single -> the value, multi -> keep list
                Object val = list.isEmpty() ? null : (list.size() == 1 ? list.get(0) : list);
                out.put(key, val);
            } else {
                out.put(key, v);
            }
        }
        return out;
    }

}