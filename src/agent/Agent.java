package agent;

import constants.Const;
import java.util.*;
import rand.randomGenerator;

public class Agent {
    private int id;
    private double opinion;
    private double stubbornness;
    private double bc; // Bounded Confidence
    private double intrinsicOpinion;
    private final int NUM_OF_AGENTS = Const.NUM_OF_SNS_USER;
    private int toPost; // % of posts at a step
    private int numOfPosts; // maximum % of posts that an agent can read at a step
    private int opinionClass;
    private PostCash postCash; // posts in feeds shall be selected from cash
    private double postProb;
    private List<Post> feed = new ArrayList<>(); // timeline
    private double useProb = Const.INITIAL_PU;
    private boolean target = false; // for further simulation like using bots
    private int timeStep;
    private boolean[] followList = new boolean[NUM_OF_AGENTS];
    private boolean[] unfollowList = new boolean[NUM_OF_AGENTS];
    private int followerNum;
    private boolean used; // whether agent uses platform or not
    private int recievedLikeCount;
    private double repostProb;
    private static final int COMFORT_MEMORY_SIZE = 100;  // 直近何ステップを保持するか
    private Deque<Double> comfortHistory = new ArrayDeque<>();


    // constructor
    public Agent(int agentID) {
        this.id = agentID;
        this.stubbornness = Const.INITIAL_STUBBORNNESS;
        this.intrinsicOpinion = Math.max(-1.0, Math.min(1.0, randomGenerator.get().nextGaussian() * Const.INITIAL_OPINION_STD)); // norm dist
        this.opinion = this.intrinsicOpinion;
        this.bc = Const.BOUNDED_CONFIDENCE; // dynamic not static
        this.postProb = Const.INITIAL_PP;
        this.timeStep = 0;
        this.recievedLikeCount = 0;
        this.repostProb = Const.REPOST_PROB;
        setNumOfPosts(10);
        setOpinionClass();
    }

    // getter methods

    public int getId() {
        return this.id;
    }

    public double getOpinion() {
        return this.opinion;
    }

    public double getIntrinsicOpinion() {
        return this.intrinsicOpinion;
    }

    public double getStubbornness() {
        return this.stubbornness;
    }

    public int getNumOfPosts() {
        return this.numOfPosts;
    }

    public int getToPost() {
        return this.toPost;
    }

    public int getOpinionClass() {
        return this.opinionClass;
    }

    public double getBc() {
        return this.bc;
    }

    public double getPostProb() {
        return this.postProb;
    }

    public List<Post> getFeed() {
        return this.feed;
    }

    public double getuseProb() {
        return this.useProb;
    }

    public int getFollwerNum() {
        return this.followerNum;
    }

    public PostCash getPostCash() {
        return this.postCash;
    }

    public boolean[] getFollowList() {
        return this.followList;
    }

    public boolean[] getUnfollowList() {
        return this.unfollowList;
    }

    public boolean getTarget() {
        return this.target;
    }

    public double getAverageComfortRate() {
        if (comfortHistory.isEmpty()) return 0.0;
        double sum = 0.0;
        for (double v : comfortHistory) sum += v;
        return sum / comfortHistory.size();
    }

    // setter methods

    public void setOpinion(double value) {
        this.opinion = value;
        setOpinionClass();
    }

    public void setPostProb(double value) {
        this.postProb = value;
    }

    public void setuseProb(double value) {
        this.useProb = value;
    }

    public void setBoundedConfidence(double value) {
        this.bc = value;
    }

    public void setTimeStep(int time) {
        this.timeStep = time;
    }

    public void setStubbornness(double value) {
        this.stubbornness = value;
    }

    public void setIntrinsicOpinion(double value) {
        this.intrinsicOpinion = value;
    }

    public void setNumOfPosts(int value) {
        this.numOfPosts = value;
        setPostCash(this.numOfPosts);
    }

    public void setPostCash(int value) {
        this.postCash = new PostCash(value);
    }

    public void setToPost(int value) {
        this.toPost = value;
    }

    public void setOpinionClass() {
        double shiftedOpinion = this.opinion + 1; // [-1,1] → [0,2]
        double opinionBinWidth = 2.0 / Const.NUM_OF_BINS_OF_OPINION;
        this.opinionClass = (int) Math.min(shiftedOpinion / opinionBinWidth, Const.NUM_OF_BINS_OF_OPINION - 1);
    }

    public void setFollowList(double[][] W) {
        for (int i = 0; i < W.length; i++) {
            if (W[this.id][i] > 0.0) {
                this.followList[i] = true;
            }
        }
    }

    public void setFollowerNum(double[][] W) {
        this.followerNum = 0;
        for (int i = 0; i < NUM_OF_AGENTS; i++) {
            if (W[i][this.id] > 0.0) {
                this.followerNum++;
            }
        }
    }

    public void setTarget() {
        this.target = true;
    }

    public void addToPostCash(Post post) {
        if (post.getPostUserId() != this.id
                && !this.unfollowList[post.getPostUserId()]) {
            this.postCash.addPost(post);
        }
    }

    public void setUsed() {
        this.used = true;
    }

    public void resetUsed() {
        this.used = false;
    }

    // other methods

    public void receiveLike() {
        this.recievedLikeCount++;
    }

    public void resetPostCash() {
        this.postCash.reset();
        this.toPost = 0;
    }

    public void addPostToFeed(Post post) {
        if (!this.unfollowList[post.getPostUserId()]) {
            this.feed.add(post);
        }
    }

    public void resetFeed() {
        this.feed.clear();
    }

    public void shufflePostCash(){
        this.postCash.shuffle();
    }

    public void updatePostProb() {
        // post prob is set based on the marginal utility theory
        double increment = Const.MU_PARAM * Math.log(this.recievedLikeCount + 1);
    
        // 100 received likes lead to approximately 1.46 times increase
        //this.postProb *= 1.0 + increment;

        this.postProb = Math.min(this.postProb, 1.0);
        this.recievedLikeCount = 0;
    }

    public void updateMyself() {
        double temp = 0.0;
        int postNum = 0;
        int comfortPostNum = 0;

        // read all posts in feed
        for (Post post : this.feed) {
            temp += post.getPostOpinion();

            postNum++;

            if (Math.abs(post.getPostOpinion() - this.opinion) < Const.MINIMUM_BC) {
                comfortPostNum++;
            }

            if (Math.abs(post.getPostOpinion() - this.opinion) > this.bc) {
                //this.bc -= Const.DECREMENT_BC * decayFunc(this.timeStep);
                this.bc *= Const.BC_DEC_RATE;
                // 0.9995だと弱い
                // 0.999でも弱い
                // 0.99だと強いかも
                // 0.995だと弱い
                // 0.99でちょうど良い
            }

        }

        if (postNum == 0)
            return;

        double comfortPostRate = (double) comfortPostNum / postNum;

        comfortHistory.addLast(comfortPostRate);
        if (comfortHistory.size() > COMFORT_MEMORY_SIZE) {
            comfortHistory.removeFirst();
        }

        if (comfortPostRate > Const.OPINION_PREVALENCE) {
            //this.postProb += Const.INCREMENT_PP * decayFunc(this.timeStep);
            this.postProb *= 1.1;
            this.useProb *= 1.1;
            //this.useProb += Const.INCREMENT_PU * decayFunc(this.timeStep);
        }else if(comfortPostRate <= 1 - Const.OPINION_PREVALENCE){ 
            //this.useProb -= Const.DECREMENT_PU * decayFunc(this.timeStep);
            //this.postProb -= Const.DECREMENT_PP * decayFunc(this.timeStep);
            this.postProb *= 0.9;
            this.useProb *= 0.9;
        }

        //// social influence

        this.opinion = this.stubbornness * this.intrinsicOpinion + (1 - this.stubbornness) * (temp / postNum);

        //// clipping

        // opinion is in [-1, 1]
        this.opinion = Math.max(-1.0, Math.min(this.opinion, 1.0));

        // postProb is in [Const.MIN_PP, Const.MAX_PP]
        this.postProb = Math.max(Const.MIN_PP, Math.min(this.postProb, Const.MAX_PP));

        // useProb is in [Const.MIN_PU, Const.MAX_PU]
        this.useProb = Math.max(Const.MIN_PU, Math.min(this.useProb, Const.MAX_PU));

        // bc is in [Const.MINIMUM_BC, 1.0]
        this.bc = Math.max(this.bc, Math.min(Const.MINIMUM_BC, 1.0));


        //// exp 
        
        if(this.target) {
            this.opinion = Const.TARGET_DIRECTION;
        }
        
        ////

        setOpinionClass();
    }

    public Post like() {
        List<Post> candidates = new ArrayList<>();
        if (this.feed.size() <= 0) {
            return null;
        }

        for (Post post : this.feed) {
            if (Math.abs(post.getPostOpinion() - this.opinion) < this.bc) {
                candidates.add(post);
            }
        }

        // choose 1 post randomly from candidates to like
        if (!candidates.isEmpty()) {
            Post likedPost = candidates.get(randomGenerator.get().nextInt(candidates.size()));
            likedPost.receiveLike();
            return likedPost;
        } else {
            return null;
        }
    }

    public List<Post> repost() {
        List<Post> candidates = new ArrayList<>();
        List<Post> repostedPostList = new ArrayList<>();
        if (this.feed.isEmpty()) {
            return Collections.emptyList();
        }

        for (Post post : this.feed) {
            if (Math.abs(post.getPostOpinion() - this.opinion) < this.bc) {
                candidates.add(post);
            }
        }

        if (!candidates.isEmpty()) {
            for (Post post : candidates) {
                if (randomGenerator.get().nextDouble() < this.repostProb) {
                    post.receiveLike();
                    repostedPostList.add(post);
                }
            }
        } else {
            return Collections.emptyList();
        }

        return repostedPostList;
    }

    /**
     * フォロー処理を行うメソッド
     * @param agents エージェント配列
     * @return int[] {新規フォローID, 解除したID}。何もしなかった場合は null を返す。
     */
    public int[] follow(Agent[] agents) {
        // 1. 候補者のリストアップ
        List<Integer> candidates = new ArrayList<>();
        for (Post post : this.feed) {
            // 既にフォローしている、またはブロック（unfollowList）している人は除外
            if (Math.abs(post.getPostOpinion() - this.opinion) < this.bc 
                    && !this.followList[post.getPostUserId()]
                    && !this.unfollowList[post.getPostUserId()]) {
                candidates.add(post.getPostUserId());
            }
        }

        // 候補がいない、または確率判定でフォローしない場合は null を返す
        if (candidates.isEmpty() || randomGenerator.get().nextDouble() >= Const.FOLLOW_PROB) {
            return new int[]{-1, -1};
        }

        // 2. 新しくフォローする相手を決定
        int newFollowId = candidates.get(randomGenerator.get().nextInt(candidates.size()));

        // 3. 上限チェックと「押し出し（アンフォロー）」処理
        int removeTargetId = -1; // 初期値は -1（誰も削除しない）

        // 現在のフォロー数を計算（※followListのサイズではなく、trueの数）
        int currentFollowCount = 0;
        for (boolean b : this.followList) {
            if (b) currentFollowCount++;
        }

        if (currentFollowCount >= Const.MAX_FOLLOW_CAPACITY) {
            double maxDiff = -1.0;

            // フォロー中の中で「最も意見が遠い」人を探す
            for (int i = 0; i < this.followList.length; i++) {
                if (this.followList[i]) { // フォローしている人だけ対象
                    double diff = Math.abs(agents[i].getOpinion() - this.opinion);
                    
                    if (diff > maxDiff) {
                        maxDiff = diff;
                        removeTargetId = i;
                    }
                }
            }

            // 最も遠い人をアンフォロー
            if (removeTargetId != -1) {
                this.followList[removeTargetId] = false;
            }
        }

        // 4. 新しいフォローを確定
        this.followList[newFollowId] = true;

        // ★ [0]:追加したID, [1]:削除したID を返す
        return new int[]{newFollowId, removeTargetId};
    }

    /*public int follow() {
        List<Integer> candidates = new ArrayList<>();

        for (Post post : this.feed) {
            if (Math.abs(post.getPostOpinion() - this.opinion) < this.bc && !this.followList[post.getPostUserId()]
                    && !this.unfollowList[post.getPostUserId()]) {
                candidates.add(post.getPostUserId());
            }
        }

        if (!candidates.isEmpty() && randomGenerator.get().nextDouble() < Const.FOLLOW_PROB) {
            int followId = candidates.get(randomGenerator.get().nextInt(candidates.size()));
            this.followList[followId] = true;

            return followId;
        }
        return -1;
    }*/

    public int unfollow() {
        int followeeNum = 0;
        for (int i = 0; i < NUM_OF_AGENTS; i++) {
            if (this.followList[i]) {
                followeeNum++;
            }
        }
        
        //if (this.feed.size() == 0 || followeeNum <= 1) {
        if (this.feed.isEmpty()) {
            return -1;
        }

        List<Integer> dislikeUser = new ArrayList<>();
        if (randomGenerator.get().nextDouble() > Const.UNFOLLOW_PROB) {
            return -1;
        }
        for (Post post : this.feed) {
            if (Math.abs(post.getPostOpinion() - this.opinion) > this.bc && this.followList[post.getPostUserId()]) {
                this.unfollowList[post.getPostUserId()] = true;
                this.followList[post.getPostUserId()] = false;
                return post.getPostUserId();
            }
            if (Math.abs(post.getPostOpinion() - this.opinion) > this.bc && !this.followList[post.getPostUserId()]) {
                dislikeUser.add(post.getPostUserId());
            }
        }
        if (dislikeUser.size() > 0) { // if there's nobody to unfollow, agents can also "block" others
            this.unfollowList[dislikeUser.get(randomGenerator.get().nextInt(dislikeUser.size()))] = true;
        }
        return -1;
    }

    public Post makePost(int step) {

        Post post;
        post = new Post(this.id, this.opinion, step);

        this.toPost = 1;

        this.postProb -= Const.POST_COST;
        if (this.postProb < Const.MIN_PP) {
            this.postProb = Const.MIN_PP;
        }

        return post;
    }

    public double decayFunc(double time) { // for the sake of convergence
        double lambda = 0.0002;
        //return Math.exp(-lambda * time);
        return 1;
    }

}
