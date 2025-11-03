package com.example.fraud.fraud;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedDeque;
import org.springframework.stereotype.Component;

@Component
public class RecentTransactions {
    private final int capacity = 300;
    private final Deque<Object> deque = new ConcurrentLinkedDeque<>();

    public void add(Object edgeId) {
        if (edgeId == null) return;
        deque.addFirst(edgeId);
        while (deque.size() > capacity) {
            deque.pollLast();
        }
    }

    public List<Object> page(int offset, int limit) {
        if (offset < 0) offset = 0;
        if (limit <= 0) limit = 100;
        List<Object> out = new ArrayList<>(limit);
        int idx = 0;
        Iterator<Object> it = deque.iterator();
        while (it.hasNext() && out.size() < limit) {
            Object id = it.next();
            if (idx++ < offset) continue;
            out.add(id);
        }
        return Collections.unmodifiableList(out);
    }

    public int size() { return deque.size(); }
}