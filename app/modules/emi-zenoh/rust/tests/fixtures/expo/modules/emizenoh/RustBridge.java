package expo.modules.emizenoh;

// Same JNI contract as the Kotlin object, without an Android/Expo dependency.
public final class RustBridge {
    public static native void initialize();
    public static native byte[] call(byte[] request);
    public static native void shutdown();

    public static volatile byte[] lastEvent;
    private static volatile boolean failNext;

    public static void failNextEvent() {
        failNext = true;
    }

    public static void onNativeEvent(byte[] bytes) {
        if (failNext) {
            failNext = false;
            throw new IllegalStateException("test listener failure");
        }
        lastEvent = bytes;
    }
}
