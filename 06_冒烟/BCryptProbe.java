public class BCryptProbe {
    public static void main(String[] args) {
        String hash = "$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK";
        System.out.println("hutool checkpw Swa@123456 => " + cn.hutool.crypto.digest.BCrypt.checkpw("Swa@123456", hash));
    }
}
