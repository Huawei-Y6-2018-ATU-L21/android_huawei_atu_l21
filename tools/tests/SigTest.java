import android.content.pm.PackageInfo;
import android.content.pm.Signature;
import java.lang.reflect.Method;
import java.security.MessageDigest;

public class SigTest {
    public static void main(String[] a) throws Exception {
        Class<?> at = Class.forName("android.app.ActivityThread");
        Object ipm = at.getMethod("getPackageManager").invoke(null);
        Method gpi = ipm.getClass().getMethod("getPackageInfo", String.class, int.class, int.class);
        for (String pkg : a) {
            PackageInfo p2 = (PackageInfo) gpi.invoke(ipm, pkg, 0x08000000 /* GET_SIGNING_CERTIFICATES */, 0);
            if (p2 != null && p2.signingInfo != null) for (Signature s : p2.signingInfo.getApkContentsSigners()) {
                byte[] d = MessageDigest.getInstance("SHA-1").digest(s.toByteArray());
                StringBuilder sb = new StringBuilder(); for (byte b : d) sb.append(String.format("%02x", b));
                System.out.println(pkg + " signingInfo: " + sb);
            }
            PackageInfo pi = (PackageInfo) gpi.invoke(ipm, pkg, 64 /* GET_SIGNATURES */, 0);
            if (pi == null || pi.signatures == null) { System.out.println(pkg + ": none"); continue; }
            for (Signature s : pi.signatures) {
                byte[] d = MessageDigest.getInstance("SHA-1").digest(s.toByteArray());
                StringBuilder sb = new StringBuilder();
                for (byte b : d) sb.append(String.format("%02x", b));
                System.out.println(pkg + ": " + sb);
            }
        }
    }
}
