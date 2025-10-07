package com.example.fraud.util;

public class Util {

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
}