package agent;

public class Post {
    private int postUserId;
    private double postOpinion;
    private int postedStep;
    private int recievedLike;
    private final int postId;
    private static int postIdCounter = 0;

    public Post(int postUserId, double postOpinion, int postedStep){
        this.postUserId = postUserId;
        this.postOpinion = postOpinion;
        this.postedStep = postedStep;
        this.recievedLike = 0;
        this.postId = postIdCounter++;
    }

    // Getter
    public int getPostUserId() {
        return postUserId;
    }

    public double getPostOpinion() {
        return postOpinion;
    }

    public int getPostedStep() {
        return postedStep;
    }

    public int getRecievedLike(){
        return this.recievedLike;
    }

    public int getPostId(){
        return this.postId;
    }

    // Setter
    public void setPostUserId(int postUserId) {
        this.postUserId = postUserId;
    }

    public void setPostOpinion(double postOpinion) {
        this.postOpinion = postOpinion;
    }

    public void setPostedStep(int postedStep) {
        this.postedStep = postedStep;
    }

    // other
    public Post copyPost(){
        Post copiedPost = new Post(this.postUserId, this.postOpinion, this.postedStep);
        return copiedPost;
    }

    public void receiveLike(){
        this.recievedLike++;
    }
}
