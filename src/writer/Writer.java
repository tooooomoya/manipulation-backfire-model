package writer;

import agent.*;
import constants.Const;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;

public class Writer {

    private int simulationStep;
    private String folderPath;
    private double opinionVar;
    private double postOpinionVar;
    private double shannonIndex;
    private double disagreement;
    private int followActionNum;
    private int unfollowActionNum;
    private String[] resultList;
    private int rewireActionNum;
    private int[] postBins = new int[Const.NUM_OF_BINS_OF_POSTS];
    private double postBinWidth;
    private int[] opinionBins = new int[Const.NUM_OF_BINS_OF_OPINION_FOR_WRITER];
    private double opinionBinWidth;
    private double opinionAvg;
    private double[] feedMeanArray;
    private double[] feedVarArray;
    private double[] cRateMeanArray;
    private double[] cRateVarArray;
    private double[] highComfortRateNumArray;

    private static final int BATCH_SIZE = 1000;
    private int batchStartStep = 0;
    private StringBuilder metricsBuf = new StringBuilder();
    private StringBuilder postsBuf = new StringBuilder();
    private StringBuilder opinionBuf = new StringBuilder();

    public Writer(String folderPath, String[] resultList) {
        this.simulationStep = -1;
        this.folderPath = folderPath;
        this.opinionVar = -1;
        this.postOpinionVar = -1;
        this.shannonIndex = -1;
        this.disagreement = -1;
        this.followActionNum = 0;
        this.unfollowActionNum = 0;
        this.rewireActionNum = 0;
        this.resultList = resultList;
        this.postBinWidth = 2.0 / postBins.length;
        this.opinionBinWidth = 2.0 / opinionBins.length;
        this.opinionAvg = 0.0;
        this.feedMeanArray = new double[Const.NUM_OF_BINS_OF_OPINION];
        this.feedVarArray = new double[Const.NUM_OF_BINS_OF_OPINION];
        this.cRateMeanArray = new double[Const.NUM_OF_BINS_OF_OPINION];
        this.cRateVarArray = new double[Const.NUM_OF_BINS_OF_OPINION];
        this.highComfortRateNumArray = new double[Const.NUM_OF_BINS_OF_OPINION];
    }

    // Setter
    public void setSimulationStep(int step) {
        this.simulationStep = step;
        this.opinionVar = -1;
    }

    public void setOpinionVar(double var) {
        this.opinionVar = var;
    }

    public void setPostOpinionVar(double var) {
        this.postOpinionVar = var;
    }

    public void setRewireActionNum(int value) {
        this.rewireActionNum = value;
    }

    public void setFollowUnfollowActionNum(int followActionNum, int unfollowActionNum) {
        this.followActionNum = followActionNum;
        this.unfollowActionNum = unfollowActionNum;
    }

    public void setOpinionAvg(double value) {
        this.opinionAvg = value;
    }

    public void setFeedMeanArray(double[] original) {
        this.feedMeanArray = original.clone();
    }

    public void setFeedVarArray(double[] original) {
        this.feedVarArray = original.clone();
    }

    public void setCRateMeanArray(double[] original) {
        this.cRateMeanArray = original.clone();
    }

    public void setCRateVarArray(double[] original) {
        this.cRateVarArray = original.clone();
    }

    public void setHighComfortRateNumArray(double[] original) {
        this.highComfortRateNumArray = original.clone();
    }

    public void setShannonIndex(double value) {
        this.shannonIndex = value;
    }

    public void setDisagreement(double value) {
        this.disagreement = value;
    }

    public void clearPostBins() {
        for (int i = 0; i < postBins.length; i++) {
            postBins[i] = 0;
        }
    }

    public void setPostBins(Post post) {
        double shiftedOpinion = post.getPostOpinion() + 1;
        int binIndex = (int) Math.min(shiftedOpinion / postBinWidth, postBins.length - 1);
        postBins[binIndex] += 1;
    }

    public void setOpinionBins(Agent[] agentSet) {
        double opinionBinWidth = 2.0 / Const.NUM_OF_BINS_OF_OPINION_FOR_WRITER;
        for (int i = 0; i < opinionBins.length; i++) {
            opinionBins[i] = 0;
        }
        for (Agent agent : agentSet) {
            if (!agent.getTarget()) {
                double shiftedOpinion = agent.getOpinion() + 1; // [-1,1] → [0,2]
                int opinionClass = (int) Math.min(shiftedOpinion / opinionBinWidth,
                        Const.NUM_OF_BINS_OF_OPINION_FOR_WRITER - 1);
                this.opinionBins[opinionClass] += 1;
            }
        }
    }

    public void write() {
        if (metricsBuf.length() == 0) {
            metricsBuf.append("step");
            for (String key : resultList) {
                metricsBuf.append(",").append(key);
            }
            metricsBuf.append("\n");
        }

        metricsBuf.append(simulationStep);
        for (String key : resultList) {
            metricsBuf.append(",");
            if (appendSingleMetric(metricsBuf, key)) {
                continue;
            }

            int lastUnderscoreIndex = key.lastIndexOf("_");
            if (lastUnderscoreIndex != -1) {
                String prefix = key.substring(0, lastUnderscoreIndex);
                String suffix = key.substring(lastUnderscoreIndex + 1);
                try {
                    int index = Integer.parseInt(suffix);
                    if (index >= 0 && index < Const.NUM_OF_BINS_OF_POSTS) {
                        switch (prefix) {
                            case "feedPostOpinionMean" -> metricsBuf.append(String.format("%.4f", this.feedMeanArray[index]));
                            case "feedPostOpinionVar" -> metricsBuf.append(String.format("%.4f", this.feedVarArray[index]));
                            case "cRateMean" -> metricsBuf.append(String.format("%.4f", this.cRateMeanArray[index]));
                            case "cRateVar" -> metricsBuf.append(String.format("%.4f", this.cRateVarArray[index]));
                            case "highComfortRateNum" -> metricsBuf.append(String.format("%.4f", this.highComfortRateNumArray[index]));
                            default -> metricsBuf.append("");
                        }
                    } else {
                        metricsBuf.append("");
                    }
                } catch (NumberFormatException e) {
                    metricsBuf.append("");
                }
            } else {
                metricsBuf.append("");
            }
        }
        metricsBuf.append("\n");

        if (postsBuf.length() == 0) {
            postsBuf.append("step");
            for (int i = 0; i < postBins.length; i++) {
                postsBuf.append(",bin_").append(i);
            }
            postsBuf.append(",sumOfPosts\n");
        }

        postsBuf.append(simulationStep);
        int sumOfPosts = 0;
        for (int i = 0; i < postBins.length; i++) {
            postsBuf.append(",").append(postBins[i]);
            sumOfPosts += postBins[i];
        }
        postsBuf.append(",").append(sumOfPosts).append("\n");

        if (opinionBuf.length() == 0) {
            opinionBuf.append("step");
            for (int i = 0; i < opinionBins.length; i++) {
                opinionBuf.append(",bin_").append(i);
            }
            opinionBuf.append("\n");
        }

        opinionBuf.append(simulationStep);
        for (int i = 0; i < opinionBins.length; i++) {
            opinionBuf.append(",").append(opinionBins[i]);
        }
        opinionBuf.append("\n");

        if (simulationStep > 0 && (simulationStep - batchStartStep + 1) >= BATCH_SIZE) {
            flushBatch();
        }
    }

    public void flush() {
        if (metricsBuf.length() > 0) {
            flushBatch();
        }
    }

    private void flushBatch() {
        int batchEnd = simulationStep;
        writeBuffer(metricsBuf, folderPath + "/metrics/result_" + batchStartStep + "_" + batchEnd + ".csv");
        writeBuffer(postsBuf, folderPath + "/posts/post_result_" + batchStartStep + "_" + batchEnd + ".csv");
        writeBuffer(opinionBuf, folderPath + "/opinion/opinion_result_" + batchStartStep + "_" + batchEnd + ".csv");

        metricsBuf.setLength(0);
        postsBuf.setLength(0);
        opinionBuf.setLength(0);
        batchStartStep = simulationStep + 1;
    }

    private void writeBuffer(StringBuilder buf, String filePath) {
        try (PrintWriter pw = new PrintWriter(new FileWriter(filePath, false))) {
            pw.print(buf);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private boolean appendSingleMetric(StringBuilder sb, String key) {
        switch (key) {
            case "opinionVar" -> {
                sb.append(String.format("%.4f", this.opinionVar));
                return true;
            }
            case "postOpinionVar" -> {
                sb.append(String.format("%.4f", this.postOpinionVar));
                return true;
            }
            case "shannonIndex" -> {
                sb.append(String.format("%.4f", this.shannonIndex));
                return true;
            }
            case "disagreement" -> {
                sb.append(String.format("%.4f", this.disagreement));
                return true;
            }
            case "follow" -> {
                sb.append(this.followActionNum);
                return true;
            }
            case "unfollow" -> {
                sb.append(this.unfollowActionNum);
                return true;
            }
            case "rewire" -> {
                sb.append(this.rewireActionNum);
                return true;
            }
            case "opinionAvg" -> {
                sb.append(String.format("%.4f", this.opinionAvg));
                return true;
            }
            default -> {
                return false;
            }
        }
    }

    public void writeDegrees(double[][] adjacencyMatrix, String outputDirPath) {
        String filePath = outputDirPath + "/degrees/degree_result_" + simulationStep + ".csv";
        try (PrintWriter pw = new PrintWriter(new FileWriter(filePath, false))) {
            pw.println("agentId,inDegree,outDegree");
            int numAgents = adjacencyMatrix.length;
            for (int i = 0; i < numAgents; i++) {
                int outDegree = 0;
                int inDegree = 0;
                for (int j = 0; j < numAgents; j++) {
                    outDegree += (adjacencyMatrix[i][j] > 0) ? 1 : 0;
                }
                for (int j = 0; j < numAgents; j++) {
                    inDegree += (adjacencyMatrix[j][i] > 0) ? 1 : 0;
                }
                pw.printf("%d,%d,%d%n", i, inDegree, outDegree);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public void writeClusteringCoefficients(double[] clustering, String outputDirPath) {
        String filePath = outputDirPath + "/clusterings/clustering_result_" + simulationStep + ".csv";
        try (PrintWriter pw = new PrintWriter(new FileWriter(filePath, false))) {
            pw.println("agentId,clusteringCoefficient");
            for (int i = 0; i < clustering.length; i++) {
                pw.printf("%d,%.6f%n", i, clustering[i]);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
