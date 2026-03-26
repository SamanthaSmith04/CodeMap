package com.aegis.bridge;

/**
 * Android JNI Bridge for Project Aegis.
 * Responsible for passing mobile file streams to the C++ BufferManager.
 */
public class NativeVault {
    static {
        System.loadLibrary("aegis_core");
    }

    public native int secureStore(byte[] data, String key);

    public void onStorageRequest(byte[] data) {
        System.out.println("Processing mobile storage request...");
        secureStore(data, "MOBILE_SECURE_KEY");
    }
}