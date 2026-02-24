package rand;

import java.util.Random;

public final class randomGenerator {

    private static Random rand;

    private randomGenerator() {}

    /** main から一度だけ呼ぶ */
    public static void init(int seed) {
        rand = new Random(seed);
    }

    /** どこからでも共通の Random を取得 */
    public static Random get() {
        if (rand == null) {
            throw new IllegalStateException("RandomGenerator not initialized");
        }
        return rand;
    }
}
