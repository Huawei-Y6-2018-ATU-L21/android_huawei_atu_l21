import android.media.MediaDrm;
import java.util.UUID;
public class DrmTest {
    public static void main(String[] a) throws Exception {
        UUID wv = new UUID(0xEDEF8BA979D64ACEL, 0xA3C827DCD51D21EDL);
        System.out.println("widevine supported: " + MediaDrm.isCryptoSchemeSupported(wv));
        MediaDrm d = new MediaDrm(wv);
        for (String p : new String[]{"vendor", "version", "securityLevel", "systemId"})
            try { System.out.println("  " + p + " = " + d.getPropertyString(p)); } catch (Throwable t) { System.out.println("  " + p + ": " + t); }
        d.close();
    }
}
