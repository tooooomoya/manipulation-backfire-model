package admin;

import agent.Agent;
import constants.Const;
import java.util.*;
import rand.randomGenerator;

public class ExpIntervention {
    private int n;
    private int[] followerNumArray;

    // コンストラクタ
    public ExpIntervention(int userNum, double[][] W) {
        this.n = userNum;
        this.followerNumArray = new int[n];
        calculateFollowerCounts(W);
    }

    // 隣接行列Wからフォロワー数を計算
    private void calculateFollowerCounts(double[][] W) {
        Arrays.fill(this.followerNumArray, 0);
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (W[i][j] > 0.0) {
                    this.followerNumArray[j]++;
                }
            }
        }
    }

    // フォロワー数のランキングを取得
    private List<Map.Entry<Integer, Integer>> getFollowerRanking() {
        List<Map.Entry<Integer, Integer>> rankingList = new ArrayList<>();

        for (int i = 0; i < n; i++) {
            rankingList.add(new AbstractMap.SimpleEntry<>(i, followerNumArray[i]));
        }

        // 降順にソート
        rankingList.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));

        return rankingList;
    }

    // --- 実験介入用のメソッド群 ---

    // Returns a randomly selected moderate influencer whose follower count
    // meets the 5% floor, so structural type varies naturally across seeds.
    public List<Integer> getManipulationTarget(Agent[] agentSet, double[][] W, int numTargets) {
        calculateFollowerCounts(W);

        int followerFloor = (int) Math.ceil(0.05 * n);

        List<Integer> pool = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            double opinion = agentSet[i].getOpinion();
            if (Math.abs(opinion) < 0.2 && followerNumArray[i] >= followerFloor) {
                pool.add(i);
            }
        }

        System.out.println("Moderate-influencer pool size: " + pool.size()
                + " (follower floor=" + followerFloor + ", requested=" + numTargets + ")");

        List<Integer> result = new ArrayList<>();
        if (!pool.isEmpty()) {
            Collections.shuffle(pool, randomGenerator.get());
            int count = Math.min(numTargets, pool.size());
            if (count < numTargets) {
                System.out.println("[WARN] Pool smaller than requested targets; using " + count + " target(s).");
            }
            for (int i = 0; i < count; i++) {
                result.add(pool.get(i));
            }
        } else {
            System.out.println("[WARN] No moderate influencer meets the follower floor; skipping targeting.");
        }

        for (int id : result) {
            System.out.println("Manipulation Target User ID: " + id
                    + ", Opinion: " + agentSet[id].getOpinion()
                    + ", Followers: " + followerNumArray[id]);
        }

        return result;
    }

    // トップインフルエンサーを取得
    public List<Integer> getTopInfluencers(int topK) {
        // 必要に応じてフォロワー数を再計算する場合はここに calculateFollowerCounts(W) を入れる
        List<Map.Entry<Integer, Integer>> rankingList = getFollowerRanking();
        List<Integer> topInfluencers = new ArrayList<>();

        for (int i = 0; i < Math.min(topK, rankingList.size()); i++) {
            topInfluencers.add(rankingList.get(i).getKey());
        }

        return topInfluencers;
    }
}