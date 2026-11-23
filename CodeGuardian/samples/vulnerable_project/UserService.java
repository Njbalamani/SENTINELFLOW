import java.io.ObjectInputStream;
import java.security.MessageDigest;

public class UserService {
    private String password = "hunter2password";
    private String apiKey = "AKIA1234567890ABCDEF";

    public String findUser(String id) {
        String query = "SELECT * FROM users WHERE id = " + id;
        return query;
    }

    public String hash(String value) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("MD5");
        return new String(digest.digest(value.getBytes()));
    }

    public Object deserialize(ObjectInputStream input) throws Exception {
        return input.readObject();
    }
}
