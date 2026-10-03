import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
public class CodecTest {
    public static void main(String[] a) {
        long t = System.currentTimeMillis();
        MediaCodecInfo[] infos = new MediaCodecList(MediaCodecList.ALL_CODECS).getCodecInfos();
        System.out.println("codecs=" + infos.length + " time=" + (System.currentTimeMillis() - t) + "ms");
        for (MediaCodecInfo i : infos) if (!i.isEncoder()) System.out.println("  " + i.getName() + " " + String.join(",", i.getSupportedTypes()));
    }
}
