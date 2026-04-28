package admin;

import agent.Agent;
import constants.Const;
import java.util.*;

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

    // ニュートラルで影響力のあるユーザー（操作対象）を取得
    public List<Integer> getManipulationTarget(Agent[] agentSet, double[][] W) {
        calculateFollowerCounts(W);
        List<Map.Entry<Integer, Integer>> rankingList = getFollowerRanking();
        
        List<Integer> neutralUsers = new ArrayList<>();
        for (Map.Entry<Integer, Integer> entry : rankingList) {
            int userId = entry.getKey();
            double opinion = agentSet[userId].getOpinion();
            
            if (Math.abs(opinion) < 0.2) {
                neutralUsers.add(userId);
            }
        }

        List<Integer> result = new ArrayList<>();
        // 元のロジックに準拠：2番目のニュートラルユーザーをターゲットにする
        if (neutralUsers.size() > 2) {
            result.add(neutralUsers.get(0));
        }

        // 対象ユーザーの情報を出力
        for (int id : result) {
            System.out.println("Manipulation Target User ID: " + id + ", Opinion: " + agentSet[id].getOpinion() + ", Followers: " + followerNumArray[id]);
        }

        // フォロワー数の閾値チェック
        // for (int id : result) {
        //     if (followerNumArray[id] < Const.FOLLOWER_THRESHOLD) {
        //         System.out.println("⚠️ [TERMINATE] Target User " + id + " has only " + followerNumArray[id] + " followers (Threshold: " + Const.FOLLOWER_THRESHOLD + ")");
        //         System.exit(0); // 正常終了
        //     }
        // }

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