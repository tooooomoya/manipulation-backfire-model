package network;

import agent.Agent;
import rand.randomGenerator;

public class RandomNetwork extends Network {
    private double connectionProbability;

    // Constructor
    public RandomNetwork(int size, double connectionProbability) {
        super(size);
        this.connectionProbability = connectionProbability;
    }

    @Override
    public void makeNetwork(Agent[] agentSet) {
        int size = getSize();
        int[][] tempMatrix = new int[size][size];

        for (int i = 0; i < size; i++) {
            for (int j = 0; j < size; j++) {
                if (i != j && randomGenerator.get().nextDouble() < connectionProbability) {
                    int posts = randomGenerator.get().nextInt(5) + 1; 
                    setEdge(i, j, posts);
                    tempMatrix[i][j] += posts;
                }
            }
        }

        // normalize
        for (int i = 0; i < size; i++) {
            int rowSum = 0;
            for (int j = 0; j < size; j++) {
                rowSum += tempMatrix[i][j];
            }
            //agentSet[i].setNumOfPosts(rowSum);
            if (rowSum > 0) {
                for (int j = 0; j < size; j++) {
                    if (tempMatrix[i][j] > 0) {
                        double value = (double) tempMatrix[i][j] / rowSum;
                        setEdge(i, j, value);
                    }
                }
            }
        }

    }
}
