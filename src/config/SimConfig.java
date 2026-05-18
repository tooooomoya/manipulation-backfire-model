package config;

import java.io.*;
import java.util.*;

/** Minimal config.yaml reader — no external dependencies. */
public class SimConfig {

    public final String topology;
    public final Map<String, String> networkParams;

    public SimConfig(String path) throws IOException {
        Map<String, String> params = new LinkedHashMap<>();
        String topo = "HolmeKim";
        boolean inNetworkParams = false;

        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            String line;
            while ((line = br.readLine()) != null) {
                String trimmed = line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#")) continue;

                boolean isIndented = line.charAt(0) == ' ' || line.charAt(0) == '\t';

                if (isIndented && inNetworkParams) {
                    int colon = trimmed.indexOf(':');
                    if (colon > 0) {
                        String key = trimmed.substring(0, colon).trim();
                        String val = trimmed.substring(colon + 1).trim()
                                           .replace("\"", "").replace("'", "");
                        if (!val.isEmpty()) params.put(key, val);
                    }
                } else {
                    inNetworkParams = false;
                    int colon = trimmed.indexOf(':');
                    if (colon < 0) continue;
                    String key = trimmed.substring(0, colon).trim();
                    String val = trimmed.substring(colon + 1).trim()
                                        .replace("\"", "").replace("'", "");
                    if (key.equals("topology") && !val.isEmpty()) {
                        topo = val;
                    } else if (key.equals("network_params") && val.isEmpty()) {
                        inNetworkParams = true;
                    }
                }
            }
        }
        this.topology = topo;
        this.networkParams = Collections.unmodifiableMap(params);
    }

    public int getInt(String key, int def) {
        String v = networkParams.get(key);
        return v != null ? Integer.parseInt(v.trim()) : def;
    }

    public double getDouble(String key, double def) {
        String v = networkParams.get(key);
        return v != null ? Double.parseDouble(v.trim()) : def;
    }
}
