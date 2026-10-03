import android.media.*;
// Plays a 2 s 440 Hz test tone (AudioTrack, USAGE_MEDIA).
public class ToneTest {
    public static void main(String[] a) throws Exception {
        int rate = 48000; short[] buf = new short[rate * 2];
        for (int i = 0; i < buf.length; i++) buf[i] = (short) (Math.sin(2 * Math.PI * 440 * i / rate) * 12000);
        AudioTrack t = new AudioTrack.Builder()
            .setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA).build())
            .setAudioFormat(new AudioFormat.Builder().setSampleRate(rate).setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build())
            .setBufferSizeInBytes(buf.length * 2).setTransferMode(AudioTrack.MODE_STATIC).build();
        t.write(buf, 0, buf.length); t.play(); Thread.sleep(2300);
        System.out.println("played, head position=" + t.getPlaybackHeadPosition() + "/" + buf.length);
        t.release();
    }
}
