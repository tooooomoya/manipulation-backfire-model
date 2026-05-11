package network;

import agent.Agent;
import java.util.*;
import rand.randomGenerator;

public class BarabasiAlbertNetwork extends Network {
    private int m; // 各ステップで新規ノードが張るリンクの本数

    /**
     * コンストラクタ
     * @param size 全ノード数
     * @param m 新規ノード追加時に既存ノードと繋ぐ本数（例: 2〜4程度が一般的）
     */
    public BarabasiAlbertNetwork(int size, int m) {
        super(size);
        this.m = m;
    }

    @Override
    public void makeNetwork(Agent[] agentSet) {
        System.out.println("start making Barabasi-Albert network");

        // 優先的選択（Preferential Attachment）を実現するためのリスト
        // ノードIDがその次数分だけ重複して格納される "ルーレット" の役割
        List<Integer> degreePool = new ArrayList<>();

        int n = getSize();
        
        // 初期ネットワークの作成（m個のノードによる完全グラフ）
        // 最初の数個のノードがないと接続先がないため
        int initialNodes = m + 1;
        if (initialNodes > n) initialNodes = n;

        // Initial seed: bidirectional complete subgraph so all seed nodes start
        // with equal total-degree weight in the pool.
        for (int i = 0; i < initialNodes; i++) {
            for (int j = i + 1; j < initialNodes; j++) {
                addEdge(i, j);
                addEdge(j, i);
                // each undirected pair contributes +1 total-degree to both endpoints
                degreePool.add(i);
                degreePool.add(j);
            }
        }

        // Grow: newNode follows m targets chosen by total-degree PA.
        // Both newNode (out-degree++) and target (in-degree++) enter the pool,
        // so new nodes are reachable from birth — this recovers gamma = 3.
        for (int newNode = initialNodes; newNode < n; newNode++) {
            Set<Integer> targets = new HashSet<>();

            while (targets.size() < this.m) {
                if (degreePool.isEmpty()) break;
                int candidate = degreePool.get(randomGenerator.get().nextInt(degreePool.size()));
                if (candidate != newNode && !targets.contains(candidate)) {
                    targets.add(candidate);
                }
            }

            for (int target : targets) {
                addEdge(newNode, target); // directed: newNode follows target only
                degreePool.add(newNode);  // newNode's out-degree++ → stays visible for future arrivals
                degreePool.add(target);   // target's in-degree++
            }
        }
    }

    /**
     * リンク設定のヘルパーメソッド（親クラスのsetEdgeをラップ）
     */
    private void addEdge(int u, int v) {
        // 親クラスの実装に合わせて重みを1に設定
        setEdge(u, v, 1);
    }
}