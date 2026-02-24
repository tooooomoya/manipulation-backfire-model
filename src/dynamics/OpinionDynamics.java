package dynamics;

import admin.*;
import agent.*;
import analysis.*;
import constants.Const;
import gephi.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import network.*;
import rand.randomGenerator;
import writer.Writer;

public class OpinionDynamics {
    private final int t = Const.MAX_SIMULATION_STEP;
    private final int agentNum = Const.NUM_OF_SNS_USER;
    private Network network;
    private final Agent[] agentSet = new Agent[agentNum];
    private Writer writer;
    private Analysis analyzer;
    private AssertionCheck ASChecker;
    private final String[] resultList = Const.RESULT_LIST;
    private final String folerPath = Const.RESULT_FOLDER_PATH;
    private GraphVisualize gephi;
    private RepostVisualize repostGephi;
    private double connectionProbability = Const.CONNECTION_PROB_OF_RANDOM_NW;
    private AdminOptim admin;
    private int[][] repostNetwork;

    // constructor
    public OpinionDynamics() {
        setFromInitial();
        // setCustomized(); // when start with a existing gexf file
        this.analyzer = new Analysis();
        this.writer = new Writer(folerPath, resultList);
        this.gephi = new GraphVisualize(0.00, agentSet, network);
        this.repostGephi = new RepostVisualize(agentSet);
        this.admin = new AdminOptim(agentNum, network.getAdjacencyMatrix());
        this.repostNetwork = new int[agentSet.length][agentSet.length];
    }

    private void setFromInitial() {
        setNetwork();
        setAgents();
    }

    private void setNetwork() {
        ///// you can change the initial network bellow
        // this.network = new RandomNetwork(agentNum, connectionProbability);
        this.network = new ConnectingNearestNeighborNetwork(agentNum, 0.3);
        // this.network = new WattsStrogatzNetwork(agentNum, 4, 0.1);
        //this.network = new BarabasiAlbertNetwork(agentNum, 3);
        /////

        this.network.makeNetwork(agentSet);
        System.out.println("finish making network");
    }

    private void setAgents() {
        double[][] tempAdjacencyMatrix = this.network.getAdjacencyMatrix();
        for (int i = 0; i < agentNum; i++) {
            agentSet[i] = new Agent(i);
            agentSet[i].setFollowList(tempAdjacencyMatrix);
            agentSet[i].setFollowerNum(tempAdjacencyMatrix);
        }
    }

    private void setCustomized() {
        this.network = new ReadNetwork(agentNum, Const.READ_NW_PATH);
        this.network.makeNetwork(agentSet);
        System.out.println("finish making network");

        double[][] tempAdjacencyMatrix = this.network.getAdjacencyMatrix();
        for (int i = 0; i < agentNum; i++) {
            agentSet[i] = new Agent(i);
            agentSet[i].setFollowList(tempAdjacencyMatrix);
        }
        GephiReader.readGraphNodes(agentSet, Const.READ_NW_PATH);
    }

    private void errorReport() {
        ASChecker.reportASError();
    }

    // main part of the experimental dynamics
    public void evolve() {
        this.ASChecker = new AssertionCheck(agentSet, network, agentNum, t);
        
        // make sure that there are at least one agent for each intrinsic opinion
        // Top three hub users will have different opinions
        double[] opinions = { 0.0, -1.0, 1.0 };
        List<Integer> topKInfluencers = admin.getTopInfluencers(opinions.length);
        Collections.shuffle(topKInfluencers, randomGenerator.get());
        for (int j = 0; j < opinions.length; j++) {
            int agentId = topKInfluencers.get(j);
            agentSet[agentId].setIntrinsicOpinion(opinions[j]);
            System.out.println("Agent " + agentId + " assigned opinion " + agentSet[agentId].getIntrinsicOpinion());
        }

        // export gexf
        gephi.updateGraph(agentSet, network);
        gephi.exportGraph(0, folerPath);

        // export metrics
        writer.setSimulationStep(0);
        writer.setOpinionVar(analyzer.computeVarianceOpinion(agentSet));
        writer.setOpinionBins(agentSet);
        writer.write();
        writer.writeDegrees(network.getAdjacencyMatrix(), folerPath);

        int followActionNum;
        int unfollowActionNum;
        int latestListSize = Const.LATEST_POST_LIST_LENGTH;

        for (int step = 1; step <= t; step++) {
            System.out.println("step = " + step);
            followActionNum = 0;
            unfollowActionNum = 0;

            analyzer.clearPostCash();
            analyzer.resetFeedMap();
            writer.clearPostBins();
            writer.setSimulationStep(step);
            double[][] W = admin.getAdjacencyMatrix();
            List<Post> postList = new ArrayList<>();

            List<Agent> shuffledAgents = new ArrayList<>(Arrays.asList(agentSet));
            Collections.shuffle(shuffledAgents, randomGenerator.get());

            if(step == 20000) {
                List<Integer> targetUsers = admin.getManipulationTarget(agentSet);
                System.out.println("Target users for manipulation: " + targetUsers);
                for(int userId : targetUsers) {
                    agentSet[userId].setTarget();
                }
            }

            for (Agent agent : shuffledAgents) {
                int agentId = agent.getId();
                agent.setFollowerNum(W);
                agent.setTimeStep(step);
                agent.resetUsed();

                // decide whether to use platform at this step
                if (randomGenerator.get().nextDouble() > agent.getuseProb()) {
                    continue;
                }
                agent.setUsed();

                // admin sets user's feed
                admin.AdminFeedback(agentId, agentSet);
                analyzer.setFeedMap(agent);
                agent.updatePostProb();

                /////// repost (like)
                List<Post> repostedPostList = agent.repost();
                for (Post repostedPost : repostedPostList) {
                    repostNetwork[agentId][repostedPost.getPostUserId()]++;
                    for (Agent otherAgent : agentSet) {
                        if (W[otherAgent.getId()][agentId] > 0.00) { // add posts to followers' feeds
                            otherAgent.addToPostCash(repostedPost);
                        }
                    }
                    agentSet[repostedPost.getPostUserId()].receiveLike();
                }

                /////// follow
                int[] followedIds = agent.follow(agentSet);

                /////// unfollow
                int unfollowedId = agent.unfollow();

                /////// post
                if (randomGenerator.get().nextDouble() < agent.getPostProb()) {
                    Post post = agent.makePost(step);
                    for (Agent otherAgent : agentSet) {
                        if (W[otherAgent.getId()][agentId] > 0.00) {
                            otherAgent.addToPostCash(post);
                        }
                    }
                    writer.setPostBins(post);
                    analyzer.setPostCash(post);
                    postList.add(post);
                }

                agent.updateMyself();
                admin.updateAdjacencyMatrix(agentId, followedIds, unfollowedId);
                agent.resetPostCash();
                agent.resetFeed();
                ASChecker.assertionChecker(agentSet, admin, agentNum, step);
                    if (followedIds[0] >= 0) {
                        followActionNum++;
                    }
                
                if (unfollowedId >= 0) {
                    unfollowActionNum++;
                }
            }

            if (step % 5000 == 0) {
                // export gexf
                network.setAdjacencyMatrix(admin.getAdjacencyMatrix());
                gephi.updateGraph(agentSet, network);
                gephi.exportGraph(step, folerPath);
                repostGephi.updateGraph(agentSet, repostNetwork, step);
                repostGephi.exportGraph(step, folerPath);
                for (int[] repostNetwork1 : repostNetwork) {
                    Arrays.fill(repostNetwork1, 0);
                }
                writer.writeDegrees(W, folerPath);
                writer.writeClusteringCoefficients(analyzer.computeClusteringCoefficients(W), folerPath);
            }
            // export metrics
            writer.setOpinionVar(analyzer.computeVarianceOpinion(agentSet));
            analyzer.computePostVariance();
            writer.setPostOpinionVar(analyzer.getPostOpinionVar());
            writer.setFollowUnfollowActionNum(followActionNum, unfollowActionNum);
            writer.setOpinionBins(agentSet);
            writer.setOpinionAvg(analyzer.computeMeanOpinion(agentSet));
            analyzer.computeFeedMetrics(agentSet);
            writer.setFeedMeanArray(analyzer.getFeedMeanArray());
            writer.setFeedVarArray(analyzer.getFeedVarArray());
            analyzer.computeCRateArray(agentSet);
            writer.setCRateMeanArray(analyzer.getCRateMeanArray());
            writer.setCRateVarArray(analyzer.getCRateVarArray());
            analyzer.computeHighComfortRateNumArray(agentSet);
            writer.setHighComfortRateNumArray(analyzer.getHighComfortRateNumArray());
            writer.write();
        }
    }

    public static void main(String[] args) {

        int seed = Integer.parseInt(args[0]);
        randomGenerator.init(seed);

        if (args.length > 1) {
            Const.TARGET_DIRECTION = Double.parseDouble(args[1]);
        }

        Const.RANDOM_SEED = seed;
        Const.RESULT_FOLDER_PATH = "results/run_" + seed + "_dir_" + Const.TARGET_DIRECTION + "/";

        String[] subfolders = {
            "clusterings",
            "degrees",
            "figures",
            "GEXF",
            "metrics",
            "opinion",
            "posts"
        };

        try {
            Path resultDir = Path.of(Const.RESULT_FOLDER_PATH);
            if (!Files.exists(resultDir)) {
                Files.createDirectories(resultDir);
            }

            // サブフォルダ作成
            for (String sub : subfolders) {
                Path subDir = resultDir.resolve(sub);
                if (!Files.exists(subDir)) {
                    Files.createDirectories(subDir);
                }
            }
        } catch (Exception e) {
            System.err.println("Failed to create result folders: " + e.getMessage());
            e.printStackTrace();
            return;
        }

        Instant start = Instant.now();
        
        OpinionDynamics simulator = new OpinionDynamics();
        simulator.evolve();

        Instant end = Instant.now();

        Duration timeElapsed = Duration.between(start, end);
        long s = timeElapsed.getSeconds();
        long h = s / 3600;
        long m = (s % 3600) / 60;
        long sec = s % 60;

        System.out.printf("Elapsed time:   %02d:%02d:%02d\n", h, m, sec);

        // print some major information about the simulation parameter

        simulator.errorReport();
    }
}
