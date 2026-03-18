package com.bionanomics.refinery.mcp;

import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Lightweight JSON object representation for building MCP responses.
 * Adapted from open-ds.ai.
 */
public class JsonMap implements Iterable<Map.Entry<String, Object>> {
    private final LinkedHashMap<String, Object> entries = new LinkedHashMap<>();

    public void put(String key, Object value) {
        entries.put(key, value);
    }

    public Object get(String key) {
        return entries.get(key);
    }

    public String getString(String key) {
        Object val = entries.get(key);
        return val instanceof String ? (String) val : null;
    }

    public JsonMap getMap(String key) {
        Object val = entries.get(key);
        return val instanceof JsonMap ? (JsonMap) val : null;
    }

    public int getInt(String key, int defaultValue) {
        Object val = entries.get(key);
        if (val instanceof Number) return ((Number) val).intValue();
        return defaultValue;
    }

    public double getDouble(String key, double defaultValue) {
        Object val = entries.get(key);
        if (val instanceof Number) return ((Number) val).doubleValue();
        return defaultValue;
    }

    public boolean getBoolean(String key, boolean defaultValue) {
        Object val = entries.get(key);
        if (val instanceof Boolean) return (Boolean) val;
        return defaultValue;
    }

    public boolean containsKey(String key) {
        return entries.containsKey(key);
    }

    public int size() {
        return entries.size();
    }

    @Override
    public Iterator<Map.Entry<String, Object>> iterator() {
        return entries.entrySet().iterator();
    }

    public String toJson() {
        StringBuilder sb = new StringBuilder();
        sb.append('{');
        boolean first = true;
        for (Map.Entry<String, Object> entry : entries.entrySet()) {
            if (!first) {
                sb.append(',');
            }
            first = false;
            sb.append('"').append(JsonUtil.escapeString(entry.getKey())).append('"');
            sb.append(':');
            sb.append(JsonUtil.valueToJson(entry.getValue()));
        }
        sb.append('}');
        return sb.toString();
    }

    @Override
    public String toString() {
        return toJson();
    }
}
