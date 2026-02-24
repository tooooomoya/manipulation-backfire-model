package analysis;

import agent.*;
import constants.Const;
import java.util.*;

public class Analysis {
    private List<Post> postCash;
    private int n;
    private double postOpinionVar;
    private List<List<Post>> feedList;
    private double[] feedMeanArray = new double[Const.NUM_OF_BINS_OF_OPINION];
    private double[] feedVarArray = new double[Const.NUM_OF_BINS_OF_OPINION];
    private double[] cRateMeanArray = new double[Const.NUM_OF_BINS_OF_OPINION];
    private double[] cRateVarArray = new double[Const.NUM_OF_BINS_OF_OPINION];
    private double[] highComfortRateNumArray = new double[Const.NUM_OF_BINS_OF_OPINION];
    private Map<Integer, List<Post>> feedMap = new HashMap<>();

    // constructor
    public Analysis() {
        this.n = Const.NUM_OF_USER;
        this.postCash = new ArrayList<>();
        this.postOpinionVar = -1;
        this.feedList = new ArrayList<>();
    }

    public double[] getFeedMeanArray() {
        return this.feedMeanArray;
    }

    public double[] getFeedVarArray() {
        return this.feedVarArray;
    }

    public double[] getCRateMeanArray() {
        return this.cRateMeanArray;
    }

    public double[] getCRateVarArray() {
        return this.cRateVarArray;
    }

    public double[] getHighComfortRateNumArray() {
        return this.highComfortRateNumArray;
    }

    public void clearPostCash() {
        postCash.clear();
    }

    public void clearFeedList() {
        this.feedList.clear();
    }

    public void setPostCash(Post post) {
        postCash.add(post.copyPost());
    }

    public void setFeedList(List<Post> feed) {
        this.feedList.add(new ArrayList<>(feed));
    }

    public void setFeedMap(Agent agent) {
        this.feedMap.put(agent.getId(), new ArrayList<>(agent.getFeed()));
    }

    public void resetFeedMap() {
        feedMap.clear();
    }

    // compute variance of inner opinions
    public double computeVarianceOpinion(Agent[] agentSet) {
        int num = 0;
        if (n == 0) {
            return -1;
        }

        double sum = 0.0;
        for (Agent agent : agentSet) {
            if (!agent.getTarget()) {
                sum += agent.getOpinion();
                num++;
            }
        }
        double mean = sum / num;

        double squaredDiffSum = 0.0;
        for (Agent agent : agentSet) {
            if (!agent.getTarget()) {
                double diff = agent.getOpinion() - mean;
                squaredDiffSum += diff * diff;
            }
        }
        return squaredDiffSum / num;
    }

    // compute mean of inner opinions
    public double computeMeanOpinion(Agent[] agentSet) {
        int num = 0;
        if (n == 0 || agentSet == null || agentSet.length == 0) {
            return -1;
        }

        double sum = 0.0;
        for (Agent agent : agentSet) {
            if (!agent.getTarget()) {
                sum += agent.getOpinion();
                num++;
            }
        }
        return sum / num;
    }

    // compute variance of opinions on posts at a step
    public double computeFeedVariance() {
        double temp = 0.0;
        int postNum = 0;

        for (List<Post> feed : this.feedList) {
            for (Post post : feed) {
                temp += post.getPostOpinion();
                postNum++;
            }
        }

        if (postNum == 0) {
            System.out.println("no post was read by users in this step.");
            return -1;
        }

        double avg = temp / postNum;

        double squaredDiffSum = 0.0;
        for (List<Post> feed : this.feedList) {
            for (Post post : feed) {
                double diff = post.getPostOpinion() - avg;
                squaredDiffSum += diff * diff;
            }
        }

        return squaredDiffSum / postNum;
    }

    // compute mean and var of every agent's feed
    public void computeFeedMetrics(Agent[] agentSet) {
        Arrays.fill(this.feedMeanArray, 0.0);
        Arrays.fill(this.feedVarArray, 0.0);

        double[] classVarianceSum = new double[Const.NUM_OF_BINS_OF_OPINION];
        int[] agentCount = new int[Const.NUM_OF_BINS_OF_OPINION];

        for (Map.Entry<Integer, List<Post>> entry : feedMap.entrySet()) {
            Integer userId = entry.getKey();
            List<Post> feed = entry.getValue();
            Agent agent = agentSet[userId];
            int classId = agent.getOpinionClass();

            if (feed.isEmpty())
                continue;

            double sum = 0.0;
            for (Post post : feed) {
                sum += post.getPostOpinion();
            }
            double mean = sum / feed.size();
            this.feedMeanArray[classId] += mean;

            double var = 0.0;
            for (Post post : feed) {
                double diff = post.getPostOpinion() - mean;
                var += diff * diff;
            }
            var /= feed.size(); // or (feed.size() - 1) for unbiased

            classVarianceSum[classId] += var;
            agentCount[classId]++;
        }

        for (int i = 0; i < Const.NUM_OF_BINS_OF_OPINION; i++) {
            if (agentCount[i] != 0) {
                this.feedVarArray[i] = classVarianceSum[i] / agentCount[i];
                this.feedMeanArray[i] = this.feedMeanArray[i] / agentCount[i];
            }
        }

    }

    // compute mean and var of every agent's comfort rate
    public void computeCRateArray(Agent[] agentSet) {
        Arrays.fill(this.cRateMeanArray, 0.0);
        Arrays.fill(this.cRateVarArray, 0.0);

        double[] classVarianceSum = new double[Const.NUM_OF_BINS_OF_OPINION];
        int[] agentCount = new int[Const.NUM_OF_BINS_OF_OPINION];

        for (Map.Entry<Integer, List<Post>> entry : feedMap.entrySet()) {
            Integer userId = entry.getKey();
            Agent agent = agentSet[userId];
            int classId = agent.getOpinionClass();

            double cRate = agent.getAverageComfortRate(); // ★ agent が持っている値を使う

            this.cRateMeanArray[classId] += cRate;
            classVarianceSum[classId] += cRate * cRate; // 後で分散を計算するため平方和を保持
            agentCount[classId]++;
        }

        // クラスごとの平均・分散を計算
        for (int i = 0; i < Const.NUM_OF_BINS_OF_OPINION; i++) {
            if (agentCount[i] != 0) {
                double mean = this.cRateMeanArray[i] / agentCount[i];
                double meanSq = classVarianceSum[i] / agentCount[i];
                double var = meanSq - mean * mean; // 分散 = E[x^2] - (E[x])^2

                this.cRateMeanArray[i] = mean;
                this.cRateVarArray[i] = var;
            }
        }
    }

    public void computePostVariance() {
        int size = postCash.size();
        if (size == 0) {
            this.postOpinionVar = -1;
            return;
        }

        double sum = 0.0;
        for (Post post : postCash) {
            sum += post.getPostOpinion();
        }
        double mean = sum / size;

        double squaredDiffSum = 0.0;
        for (Post post : postCash) {
            double diff = post.getPostOpinion() - mean;
            squaredDiffSum += diff * diff;
        }
        this.postOpinionVar = squaredDiffSum / size;
    }

    public double getPostOpinionVar() {
        return postOpinionVar;
    }

    public double[] computeClusteringCoefficients(double[][] adj) {
        double[] clustering = new double[n];

        for (int i = 0; i < n; i++) {

            Set<Integer> neighbors = new HashSet<>();
            for (int j = 0; j < n; j++) {
                if (adj[i][j] > 0.0)
                    neighbors.add(j); // out-neighbor
                if (adj[j][i] > 0.0)
                    neighbors.add(j); // in-neighbor
            }
            neighbors.remove(i);

            int k_total = neighbors.size();
            if (k_total < 2) {
                clustering[i] = 0.0;
                continue;
            }

            int linkCount = 0;
            for (int u : neighbors) {
                for (int v : neighbors) {
                    if (u != v && adj[u][v] > 0.0) {
                        linkCount++;
                    }
                }
            }

            clustering[i] = (double) linkCount / (k_total * (k_total - 1));
        }

        return clustering;
    }

    public void computeHighComfortRateNumArray(Agent[] agentSet) {
        Arrays.fill(this.highComfortRateNumArray, 0.0);

        for (Agent agent : agentSet) {
            int classId = agent.getOpinionClass();
            double cRate = agent.getAverageComfortRate();
            if (cRate >= Const.OPINION_PREVALENCE) {
                this.highComfortRateNumArray[classId] += 1.0;
            }
        }
    }
}