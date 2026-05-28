package com.example.yourapp;  // 팀원 패키지명으로 변경

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;

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
 *
 * [단일 이미지 추론]
 *   Result r = classifier.predict(bitmap);
 *   r.label / r.confidence / r.isHealthy
 *
 * [그리드 추론 - 병반 위치 탐지]
 *   GridResult g = classifier.predictGrid(bitmap, 20);
 *   Bitmap overlay = g.drawOverlay(bitmap);
 *   g.grid[row][col].label  // 각 셀의 진단 결과
 */
public class PlantDiseaseClassifier {

    // ── 단일 추론 결과 ────────────────────────────────────────────
    public static class Result {
        public final String label;
        public final float confidence;
        public final boolean isHealthy;

        Result(String label, float confidence) {
            this.label = label;
            this.confidence = confidence;
            this.isHealthy = label.contains("Healthy");
        }

        @Override
        public String toString() {
            return String.format("%s (%.1f%%)", label, confidence * 100);
        }
    }

    // ── 그리드 추론 결과 ──────────────────────────────────────────
    public static class GridResult {
        public final Result[][] grid;   // [row][col]
        public final int gridSize;
        public final int diseaseCount;
        public final int totalCells;

        GridResult(Result[][] grid) {
            this.grid = grid;
            this.gridSize = grid.length;
            int disease = 0, total = 0;
            for (Result[] row : grid)
                for (Result cell : row) {
                    total++;
                    if (!cell.isHealthy) disease++;
                }
            this.diseaseCount = disease;
            this.totalCells = total;
        }

        public float diseaseRatio() {
            return totalCells == 0 ? 0 : (float) diseaseCount / totalCells;
        }

        /** 원본 Bitmap 위에 그리드 오버레이를 그려서 반환 */
        public Bitmap drawOverlay(Bitmap original) {
            Bitmap out = original.copy(Bitmap.Config.ARGB_8888, true);
            Canvas canvas = new Canvas(out);
            Paint paint = new Paint();
            paint.setStyle(Paint.Style.FILL);

            float cellW = (float) out.getWidth()  / gridSize;
            float cellH = (float) out.getHeight() / gridSize;

            for (int r = 0; r < gridSize; r++) {
                for (int c = 0; c < gridSize; c++) {
                    Result cell = grid[r][c];
                    if (cell.isHealthy) {
                        // 건강: 연초록 반투명
                        paint.setColor(Color.argb(60, 50, 200, 50));
                    } else {
                        // 병해: 신뢰도에 따라 빨간색 농도 조절
                        int alpha = (int) (80 + cell.confidence * 120);
                        paint.setColor(Color.argb(alpha, 220, 50, 50));
                    }
                    float left   = c * cellW;
                    float top    = r * cellH;
                    canvas.drawRect(new RectF(left, top, left + cellW, top + cellH), paint);
                }
            }

            // 셀 테두리
            paint.setStyle(Paint.Style.STROKE);
            paint.setColor(Color.argb(80, 255, 255, 255));
            paint.setStrokeWidth(1f);
            for (int r = 0; r <= gridSize; r++)
                canvas.drawLine(0, r * cellH, out.getWidth(), r * cellH, paint);
            for (int c = 0; c <= gridSize; c++)
                canvas.drawLine(c * cellW, 0, c * cellW, out.getHeight(), paint);

            return out;
        }
    }

    // ── 상수 ─────────────────────────────────────────────────────
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

    // ── 초기화 ───────────────────────────────────────────────────
    public PlantDiseaseClassifier(Context context) throws Exception {
        env = OrtEnvironment.getEnvironment();
        InputStream is = context.getAssets().open("best_crop_model.onnx");
        byte[] modelBytes = is.readAllBytes();
        is.close();
        session = env.createSession(modelBytes, new OrtSession.SessionOptions());
    }

    // ── 단일 추론 ────────────────────────────────────────────────
    public Result predict(Bitmap bitmap) throws Exception {
        float[] logits = runModel(bitmap);
        return argmaxToResult(logits);
    }

    // ── 그리드 추론 ──────────────────────────────────────────────
    /**
     * 이미지를 gridSize×gridSize 격자로 나눠 각 셀을 추론
     * @param bitmap   입력 이미지
     * @param gridSize 격자 크기 (예: 20 → 20×20=400셀)
     */
    public GridResult predictGrid(Bitmap bitmap, int gridSize) throws Exception {
        int imgW = bitmap.getWidth();
        int imgH = bitmap.getHeight();
        int cellW = imgW / gridSize;
        int cellH = imgH / gridSize;

        Result[][] grid = new Result[gridSize][gridSize];
        for (int r = 0; r < gridSize; r++) {
            for (int c = 0; c < gridSize; c++) {
                int x = c * cellW;
                int y = r * cellH;
                int w = (c == gridSize - 1) ? imgW - x : cellW;
                int h = (r == gridSize - 1) ? imgH - y : cellH;
                Bitmap cell = Bitmap.createBitmap(bitmap, x, y, w, h);
                grid[r][c] = predict(cell);
                cell.recycle();
            }
        }
        return new GridResult(grid);
    }

    // ── 내부 헬퍼 ────────────────────────────────────────────────
    private float[] runModel(Bitmap bitmap) throws Exception {
        Bitmap resized = Bitmap.createScaledBitmap(bitmap, IMG_SIZE, IMG_SIZE, true);
        int[] pixels = new int[IMG_SIZE * IMG_SIZE];
        resized.getPixels(pixels, 0, IMG_SIZE, 0, 0, IMG_SIZE, IMG_SIZE);

        float[] input = new float[3 * IMG_SIZE * IMG_SIZE];
        for (int c = 0; c < 3; c++)
            for (int i = 0; i < pixels.length; i++) {
                float val = ((pixels[i] >> (16 - c * 8)) & 0xFF) / 255.0f;
                input[c * IMG_SIZE * IMG_SIZE + i] = (val - MEAN[c]) / STD[c];
            }

        long[] shape = {1, 3, IMG_SIZE, IMG_SIZE};
        OnnxTensor tensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(input), shape);
        OrtSession.Result result = session.run(Map.of("input", tensor));
        float[] logits = ((float[][]) result.get(0).getValue())[0];
        tensor.close();
        result.close();
        return logits;
    }

    private Result argmaxToResult(float[] logits) {
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
        try { session.close(); env.close(); } catch (Exception ignored) {}
    }
}
