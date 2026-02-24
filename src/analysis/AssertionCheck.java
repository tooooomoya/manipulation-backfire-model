package analysis;

import admin.*;
import agent.Agent;
import network.*;

public class AssertionCheck {
    private Agent[] agentSet;
    private Network network;
    private int n;
    private int[] numOfError;
    private int maxStep;

    public AssertionCheck(Agent[] agentSet, Network network, int agentNum, int maxStep) {
        this.agentSet = agentSet;
        this.network = network;
        this.n = agentNum;
        this.numOfError = new int[maxStep + 1];
        this.maxStep = maxStep;
    }

    public void assertionChecker(Agent[] agentSet, AdminOptim admin, int agentNum, int step) {
        double[][] tempAdjMatrix = admin.getAdjacencyMatrix();

        for(int i = 0 ; i < n ; i ++){
            for(int j = 0; j < n ; j ++){
                if(tempAdjMatrix[i][j] > 0.0){
                    if(!agentSet[i].getFollowList()[j] || agentSet[i].getUnfollowList()[j]){
                        System.out.println("follow, unfollow list consistency with W matrix error in " + i + ", " + j);
                        System.out.println("follow list " + agentSet[i].getFollowList()[j] + ", unfollow list " + agentSet[i].getUnfollowList()[j] + ", W " +tempAdjMatrix[i][j]);
                    }
                }
            }
        }

        // opinion should be in [-1, 1]
        for(int i = 0 ; i < n ; i++){
            if(agentSet[i].getOpinion() < -1 || agentSet[i].getOpinion() > 1){
                System.out.println("AC Error: opinion is out of the range in user " + i);
                numOfError[step] ++;
            }
        }
    }

    public void reportASError(){
        int sumError = 0;
        for(int i = 0; i < maxStep ; i++){
                sumError += numOfError[i];
        }
        System.out.println("the sum of error reported : " + sumError);
    }
}