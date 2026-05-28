package com.example.yourapp;  // 팀원 패키지명으로 변경

import android.content.Context;
import android.graphics.Bitmap;

import java.io.InputStream;
import java.nio.FloatBuffer;
import java.util.Map;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;

/**
 * 식물 병해 진단 분류기
 *
 * [사용법]
 * 1. app/src/main/assets/ 에 best_crop_model.onnx 복사
 * 2. build.gradle에 추가:
 *    implementation 'com.microsoft.onnxruntime:onnxruntime-android:1.20.0'
 * 3. AndroidManifest.xml에 추가:
 *    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
 *    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
 *
 * [예시]
 *   PlantDiseaseClassifier classifier = new PlantDiseaseClassifier(context);
 *   PlantDiseaseClassifier.Result result = classifier.predict(bitmap);
 *   String label = result.label;      // "Tomato: Early Blight"
 *   float  conf  = result.confidence; // 0.0 ~ 1.0
 *   classifier.close();
 */
public class PlantDiseaseClassifier {

    public static class Result {
        public final String label;
        public final float confidence;
        public final boolean isHealthy;

        Result(String label, float confidence) {
            this.label = label;
            this.confidence = confidence;
            this.isHealthy = label.contains("Healthy");
        }
    }

    private static final String[] CLASSES = {
        "Potato: Early Blight", "Potato: Late Blight", "Potato: Healthy",
        "Tomato: Bacterial Spot", "Tomato: Early Blight", "Tomato: Late Blight",
        "Tomato: Leaf Mold", "Tomato: Septoria Leaf Spot",
        "Tomato: Spider Mites", "Tomato: Target Spot",
        "Tomato: Yellow Leaf Curl Virus", "Tomato: Mosaic Virus",
        "Tomato: Healthy", "Pepper: Bacterial Spot", "Pepper: Healthy",
        "Apple: Apple Scab", "Apple: Black Rot", "Apple: Cedar Apple Rust",
        "Apple: Healthy",
        "Corn: Cercospora / Gray Leaf Spot",
        "Corn: Common Rust", "Corn: Northern Leaf Blight",
        "Corn: Healthy"
    };

    private static final float[] MEAN = {0.485f, 0.456f, 0.406f};
    private static final float[] STD  = {0.229f, 0.224f, 0.225f};
    private static final int IMG_SIZE = 224;

    private final OrtEnvironment env;
    private final OrtSession session;

    public PlantDiseaseClassifier(Context context) throws Exception {
        env = OrtEnvironment.getEnvironment();
        InputStream is = context.getAssets().open("best_crop_model.onnx");
        byte[] modelBytes = is.readAllBytes();
        is.close();
        session = env.createSession(modelBytes, new OrtSession.SessionOptions());
    }

    public Result predict(Bitmap bitmap) throws Exception {
        Bitmap resized = Bitmap.createScaledBitmap(bitmap, IMG_SIZE, IMG_SIZE, true);

        int[] pixels = new int[IMG_SIZE * IMG_SIZE];
        resized.getPixels(pixels, 0, IMG_SIZE, 0, 0, IMG_SIZE, IMG_SIZE);

        float[] input = new float[3 * IMG_SIZE * IMG_SIZE];
        for (int c = 0; c < 3; c++) {
            for (int i = 0; i < pixels.length; i++) {
                float val = ((pixels[i] >> (16 - c * 8)) & 0xFF) / 255.0f;
                input[c * IMG_SIZE * IMG_SIZE + i] = (val - MEAN[c]) / STD[c];
            }
        }

        long[] shape = {1, 3, IMG_SIZE, IMG_SIZE};
        OnnxTensor tensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(input), shape);
        OrtSession.Result ortResult = session.run(Map.of("input", tensor));
        float[] logits = ((float[][]) ortResult.get(0).getValue())[0];
        tensor.close();
        ortResult.close();

        // softmax
        float max = logits[0];
        for (float v : logits) if (v > max) max = v;
        float sum = 0;
        float[] probs = new float[logits.length];
        for (int i = 0; i < logits.length; i++) {
            probs[i] = (float) Math.exp(logits[i] - max);
            sum += probs[i];
        }
        int maxIdx = 0;
        for (int i = 0; i < probs.length; i++) {
            probs[i] /= sum;
            if (probs[i] > probs[maxIdx]) maxIdx = i;
        }

        return new Result(CLASSES[maxIdx], probs[maxIdx]);
    }

    public void close() {
        try {
            session.close();
            env.close();
        } catch (Exception ignored) {}
    }
}
