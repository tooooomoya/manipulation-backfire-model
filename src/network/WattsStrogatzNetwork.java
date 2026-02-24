package network;

import agent.Agent;
import rand.randomGenerator;

public class WattsStrogatzNetwork extends Network {
    private int K; // 各ノードの平均次数（偶数である必要があります）
    private double beta; // 配線換え確率 (0 <= beta <= 1)

    /**
     * コンストラクタ
     * @param size ネットワークのノード数
     * @param K 平均次数（近隣ノード数）。例えば4なら左右2つずつと繋がります。
     * @param beta 配線換え確率。0なら正規格子、1ならランダムグラフに近づきます。
     */
    public WattsStrogatzNetwork(int size, int K, double beta) {
        super(size);
        this.K = K;
        this.beta = beta;
    }

    @Override
    public void makeNetwork(Agent[] agentSet) {
        System.out.println("start making Watts-Strogatz network");

        int n = getSize();
        int halfK = this.K / 2;

        // Step 1: 正規リング格子（Regular Ring Lattice）の作成
        // 各ノードを、右隣の halfK 個のノードと接続する（無向グラフとして処理）
        for (int i = 0; i < n; i++) {
            for (int j = 1; j <= halfK; j++) {
                int neighbor = (i + j) % n; // リング状にするための剰余計算
                setEdge(i, neighbor, 1);
                setEdge(neighbor, i, 1);
            }
        }

        // Step 2: 配線換え（Rewiring）
        // 各リンクについて、確率 beta でランダムな接続先に変更する
        for (int i = 0; i < n; i++) {
            for (int j = 1; j <= halfK; j++) {
                if (randomGenerator.get().nextDouble() < this.beta) {
                    int originalNeighbor = (i + j) % n;

                    // 既存のリンクを削除 (adjacencyMatrixに直接アクセスできると仮定、もしくはsetEdge(u, v, 0))
                    // setEdgeの実装によりますが、ここでは行列の値を0にして削除とみなします
                    adjacencyMatrix[i][originalNeighbor] = 0;
                    adjacencyMatrix[originalNeighbor][i] = 0;

                    // 新しい接続先を探す
                    // 条件: 自分自身ではなく、かつ既にリンクが存在しないノード
                    int newNeighbor = -1;
                    boolean found = false;
                    
                    // 無限ループ防止のための安全策（通常、疎なグラフではすぐに決まります）
                    int attempts = 0;
                    while (attempts < n) {
                        int candidate = randomGenerator.get().nextInt(n);
                        
                        boolean isSelf = (candidate == i);
                        // 行列の値を見てリンクの有無を確認
                        boolean isConnected = (adjacencyMatrix[i][candidate] > 0);

                        if (!isSelf && !isConnected) {
                            newNeighbor = candidate;
                            found = true;
                            break;
                        }
                        attempts++;
                    }

                    // 適切な接続先が見つかった場合のみリンクを張る
                    // (見つからなかった場合はリンクを削除したままにするか、元のリンクを戻す実装もありますが、
                    // WSモデルの標準的な実装では「多重辺・自己ループを避けて再接続」を行います)
                    if (found) {
                        setEdge(i, newNeighbor, 1);
                        setEdge(newNeighbor, i, 1);
                    } else {
                        // 接続先が見つからなかった場合（ほぼあり得ませんが）、元のリンクを戻す
                        setEdge(i, originalNeighbor, 1);
                        setEdge(originalNeighbor, i, 1);
                    }
                }
            }
        }
    }
}