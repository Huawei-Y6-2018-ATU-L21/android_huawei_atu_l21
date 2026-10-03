import android.media.MediaCodec;
import android.media.MediaFormat;
public class DecTest {
    public static void main(String[] a) throws Exception {
        String[][] tests = {{"c2.android.avc.decoder","video/avc"},{"c2.android.vp9.decoder","video/x-vnd.on2.vp9"},{"c2.android.aac.decoder","audio/mp4a-latm"}};
        for (String[] t : tests) {
            long st = System.currentTimeMillis();
            try {
                MediaCodec c = MediaCodec.createByCodecName(t[0]);
                MediaFormat f = t[1].startsWith("video") ? MediaFormat.createVideoFormat(t[1], 640, 360)
                        : MediaFormat.createAudioFormat(t[1], 44100, 2);
                if (!t[1].startsWith("video")) f.setByteBuffer("csd-0", java.nio.ByteBuffer.wrap(new byte[]{0x12, 0x10}));
                c.configure(f, null, null, 0);
                c.start();
                int idx = c.dequeueInputBuffer(500000);
                c.stop(); c.release();
                System.out.println(t[0] + ": OK (input idx=" + idx + ", " + (System.currentTimeMillis()-st) + "ms)");
            } catch (Throwable e) {
                System.out.println(t[0] + ": FAIL " + e);
            }
        }
    }
}
