package network;

import agent.Agent;
import java.util.*;
import rand.randomGenerator;

public class ConnectingNearestNeighborNetwork extends Network {
    private double p; // prob of converting a potential edge to an actual edge
    private double r; // prob of adding a random link instead of a potential edge (CNNR variant)
    private Set<Edge> potentialEdges;

    private static class Edge {
        int from, to;

        Edge(int from, int to) {
            this.from = from;
            this.to = to;
        }

        @Override
        public boolean equals(Object o) {
            if (!(o instanceof Edge))
                return false;
            Edge other = (Edge) o;
            return this.from == other.from && this.to == other.to;
        }

        @Override
        public int hashCode() {
            return Objects.hash(from, to);
        }
    }

    public ConnectingNearestNeighborNetwork(int size, double p, double r) {
        super(size);
        this.p = p;
        this.r = r;
        this.potentialEdges = new HashSet<>();
    }

    @Override
    public void makeNetwork(Agent[] agentSet) {
        System.out.println("start making network");

        int currentSize = 2;

        setEdge(0, 1, 1.0);

        while (currentSize < getSize()) {
            if (randomGenerator.get().nextDouble() < 1 - this.p) {
                // add new node; connect it to a random existing node (directed: newNode → v)
                int newNode = currentSize++;
                int v = randomGenerator.get().nextInt(newNode);
                setEdge(newNode, v, 1.0);

                // neighbors that v points to become potential targets for newNode
                for (int neighbor = 0; neighbor < newNode; neighbor++) {
                    if (adjacencyMatrix[v][neighbor] > 0 && neighbor != newNode) {
                        potentialEdges.add(new Edge(newNode, neighbor));
                    }
                }
            } else {
                if (randomGenerator.get().nextDouble() < 1 - this.r) {
                    // convert a potential edge to an actual directed edge
                    if (!potentialEdges.isEmpty()) {
                        List<Edge> list = new ArrayList<>(potentialEdges);
                        list.sort(Comparator.comparingInt((Edge e) -> e.from).thenComparingInt(e -> e.to));
                        Edge edge = list.get(randomGenerator.get().nextInt(list.size()));
                        setEdge(edge.from, edge.to, 1.0);
                        potentialEdges.remove(edge);
                    }
                } else {
                    // add a random directed edge (CNNR variant)
                    int a = randomGenerator.get().nextInt(currentSize);
                    int b;
                    do {
                        b = randomGenerator.get().nextInt(currentSize);
                    } while (a == b || adjacencyMatrix[a][b] > 0);
                    setEdge(a, b, 1.0);
                }
            }
        }
    }
}
