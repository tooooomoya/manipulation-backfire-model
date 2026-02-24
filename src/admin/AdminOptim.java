package admin;

import agent.*;
import constants.Const;
import java.util.*;
import rand.randomGenerator;

public class AdminOptim {
    private int n;
    private double[][] W; // Admin can operate adjacency matrix like link recommending
    private int[] followerNumArray;
    private List<Post> recommendPostQueue = new ArrayList<>();
    private int maxRecommPostQueueLength = Const.MAX_RECOMMENDATION_POST_LENGTH;


    public AdminOptim(int userNum, double[][] W) {
        this.n = userNum;
        this.W = W;
        this.followerNumArray = new int[n];
    }

    public double[][] getAdjacencyMatrix() {
        double[][] copy = new double[n][n];
        for (int i = 0; i < n; i++) {
            copy[i] = Arrays.copyOf(this.W[i], n);
        }
        return copy;
    }

    public int[] getFollowerList() {
        return this.followerNumArray.clone();
    }

    public List<Map.Entry<Integer, Integer>> getFollowerRanking() {
        List<Map.Entry<Integer, Integer>> rankingList = new ArrayList<>();

        for (int i = 0; i < n; i++) {
            rankingList.add(new AbstractMap.SimpleEntry<>(i, followerNumArray[i]));
        }

        rankingList.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));

        return rankingList;
    }


    public void setW(double[][] W) {
        this.W = W.clone();
        setFollowerNumArray();
    }

    public void setFollowerNumArray() {
        Arrays.fill(this.followerNumArray, 0);
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (this.W[i][j] > 0.0) {
                    this.followerNumArray[j]++;
                }
            }
        }
    }

    public void addRecommendPost(Post post) {
        if (recommendPostQueue.size() >= this.maxRecommPostQueueLength) {
            recommendPostQueue.remove(0); // 先頭（古い投稿）を削除
        }
        recommendPostQueue.add(post); // 新しい投稿を追加
    }

    public void updateAdjacencyMatrix(int userId, int[] followedIds, int unfollowedId) {
        if (followedIds[0] >= 0) {
            this.W[userId][followedIds[0]] = 1.0;
        }
        if(followedIds[1] >= 0) {
            this.W[userId][followedIds[1]] = 0.0;
        }
        if (unfollowedId >= 0) {
            this.W[userId][unfollowedId] = 0.0;
        }

        setFollowerNumArray();
    }

    public void AdminFeedback(int userId, Agent[] agentSet) {
        List<Post> tempFeed = new ArrayList<>();

        for (Post post : agentSet[userId].getPostCash().getAllPosts()) {
            if (!agentSet[userId].getUnfollowList()[post.getPostUserId()]) { // just for confirmation
                tempFeed.add(post);
            }
        }

        Collections.shuffle(tempFeed, randomGenerator.get());
        for (Post post : tempFeed) {
            agentSet[userId].addPostToFeed(post);
        }

    }

    // clip neutral users who have too many followers
    public List<Integer> getManipulationTarget(Agent[] agentSet) {
        List<Map.Entry<Integer, Integer>> rankingList = getFollowerRanking();
        
        List<Integer> neutralUsers = new ArrayList<>();
        for (Map.Entry<Integer, Integer> entry : rankingList) {
            int userId = entry.getKey();
            int followerNum = entry.getValue();
            double opinion = agentSet[userId].getOpinion();
            //if (Math.abs(opinion) < 0.2 && followerNum < (int) (Const.NUM_OF_USER * 0.2)) {
            if (Math.abs(opinion) < 0.2 ) {
                neutralUsers.add(userId);
            }
        }

        List<Integer> result = new ArrayList<>();
        if (neutralUsers.size() > 2) result.add(neutralUsers.get(1));
        if (neutralUsers.size() > 3) result.add(neutralUsers.get(2));

        // print the size of target users
        for (int id : result) {
            System.out.println("Manipulation Target User ID: " + id + ", Opinion: " + agentSet[id].getOpinion() + ", Followers: " + followerNumArray[id]);
        }

        for (int id : result) {
            if (followerNumArray[id] < Const.FOLLOWER_THRESHOLD) {
                System.out.println("⚠️ [TERMINATE] Target User " + id + " has only " + followerNumArray[id] + " followers (Threshold: " + Const.FOLLOWER_THRESHOLD + ")");
                System.exit(0); //正常終了
            }
        }

        return result;
    }

    public List<Integer> getTopInfluencers(int topK) {
        setFollowerNumArray();
        List<Map.Entry<Integer, Integer>> rankingList = getFollowerRanking();
        List<Integer> topInfluencers = new ArrayList<>();

        for (int i = 0; i < Math.min(topK, rankingList.size()); i++) {
            topInfluencers.add(rankingList.get(i).getKey());
        }

        return topInfluencers;
    }

}
