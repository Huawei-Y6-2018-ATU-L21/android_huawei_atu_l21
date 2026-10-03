import android.graphics.ImageFormat;
import android.media.*;
import android.os.Looper;
import java.nio.ByteBuffer;
// Decodes an mp4 into an ImageReader surface (the surface path used by browsers/video apps).
public class SurfTest {
    public static void main(String[] a) throws Exception {
        Looper.prepare();
        String codecName = a.length > 1 ? a[1] : "c2.android.avc.decoder";
        MediaExtractor ex = new MediaExtractor();
        ex.setDataSource(a[0]);
        ex.selectTrack(0);
        MediaFormat f = ex.getTrackFormat(0);
        ImageReader ir = ImageReader.newInstance(f.getInteger(MediaFormat.KEY_WIDTH), f.getInteger(MediaFormat.KEY_HEIGHT),
                ImageFormat.PRIVATE, 4, 0x100 /* GPU_SAMPLED_IMAGE */);
        ir.setOnImageAvailableListener(r -> { Image i = r.acquireLatestImage(); if (i != null) i.close(); }, null);
        MediaCodec c = MediaCodec.createByCodecName(codecName);
        c.configure(f, ir.getSurface(), null, 0);
        c.start();
        MediaCodec.BufferInfo bi = new MediaCodec.BufferInfo();
        int out = 0; boolean eos = false; long t0 = System.currentTimeMillis();
        while (out < 60 && System.currentTimeMillis() - t0 < 15000) {
            if (!eos) {
                int ii = c.dequeueInputBuffer(10000);
                if (ii >= 0) {
                    ByteBuffer b = c.getInputBuffer(ii);
                    int n = ex.readSampleData(b, 0);
                    if (n < 0) { c.queueInputBuffer(ii, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM); eos = true; }
                    else { c.queueInputBuffer(ii, 0, n, ex.getSampleTime(), 0); ex.advance(); }
                }
            }
            int oi = c.dequeueOutputBuffer(bi, 10000);
            if (oi >= 0) { c.releaseOutputBuffer(oi, true); out++; if ((bi.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) break; }
        }
        System.out.println(codecName + ": frames decoded to surface=" + out + " time=" + (System.currentTimeMillis() - t0) + "ms");
        c.stop(); c.release(); ir.close();
    }
}
