package dynamics;

import constants.Const;
import config.SimConfig;
import network.*;
import rand.randomGenerator;
import agent.Agent;
import java.io.*;

/**
 * Standalone INITIAL-network dumper for the Table NWMetrics recomputation.
 *
 * Reproduces the step-0 topology that OpinionDynamics would build for a given
 * config.yaml and seed, WITHOUT running the 40,000-step dynamics. Faithfulness:
 * OpinionDynamics.main() calls randomGenerator.init(seed) and then builds the
 * network before any dynamics, so replaying init(seed) + the same constructor
 * yields the byte-identical initial network (the degree sequence / structure the
 * NWMetrics table is computed on). Writes one directed edge list per seed
 * (line "a b" == adjacency a->b == "a follows b"), to be consumed by networkx.
 *
 * Usage: java ... dynamics.NetworkDump <nSeeds> <outDir>
 *   config.yaml selects the topology + params (same as the sweep).
 */
public class NetworkDump {
    public static void main(String[] args) throws Exception {
        int nSeeds  = args.length > 0 ? Integer.parseInt(args[0]) : 20;
        String outDir = args.length > 1 ? args[1] : "netdump";
        int agentNum = Const.NUM_OF_SNS_USER;

        SimConfig cfg = new SimConfig("config.yaml");
        System.out.println("[DUMP] topology=" + cfg.topology + " params=" + cfg.networkParams
                + " nSeeds=" + nSeeds);
        new File(outDir).mkdirs();

        for (int seed = 0; seed < nSeeds; seed++) {
            randomGenerator.init(seed);   // identical RNG seeding to OpinionDynamics.main
            Network network;
            switch (cfg.topology) {
                case "HolmeKim" -> network = new HolmeKimNetwork(agentNum,
                        cfg.getInt("m", 3), cfg.getInt("A", 1), cfg.getDouble("pt", 0.3));
                case "CNNR"     -> network = new ConnectingNearestNeighborNetwork(agentNum,
                        cfg.getDouble("p", 0.3), cfg.getDouble("r", 0.01));
                case "WS"       -> network = new WattsStrogatzNetwork(agentNum,
                        cfg.getInt("K", 4), cfg.getDouble("beta", 0.1));
                case "ER"       -> network = new RandomNetwork(agentNum,
                        cfg.getDouble("p", 0.003));
                default -> throw new RuntimeException("unsupported topology: " + cfg.topology);
            }
            Agent[] agentSet = new Agent[agentNum];
            network.makeNetwork(agentSet);
            double[][] adj = network.getAdjacencyMatrix();

            File f = new File(outDir, cfg.topology + "_seed" + seed + ".edges");
            try (PrintWriter pw = new PrintWriter(new BufferedWriter(new FileWriter(f)))) {
                for (int i = 0; i < agentNum; i++) {
                    for (int j = 0; j < agentNum; j++) {
                        if (adj[i][j] != 0.0) pw.println(i + " " + j);
                    }
                }
            }
        }
        System.out.println("[DUMP] wrote " + nSeeds + " edge lists to " + outDir + "/");
    }
}
