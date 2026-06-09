package com.example.smartfarm.worker;

import android.content.Context;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.core.content.ContextCompat;
import androidx.lifecycle.Lifecycle;
import androidx.lifecycle.LifecycleOwner;
import androidx.lifecycle.LifecycleRegistry;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import com.example.smartfarm.model.AnalyzeResponse;
import com.example.smartfarm.model.Field;
import com.example.smartfarm.network.ApiClient;
import com.example.smartfarm.network.ApiService;

import java.io.File;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * WorkManager Worker — 매일 14:00에 실행되어 모든 구역 사진을 촬영하고 서버에 업로드합니다.
 *
 * 사용법:
 *   MainActivity.scheduleDailyCapture() 에서 등록됩니다.
 *   실제 카메라 촬영은 CameraX ImageCapture API를 사용합니다.
 *   각 구역(field)에 대해 순차적으로 이미지를 찍어 /analyze 엔드포인트로 전송합니다.
 */
public class CameraWorker extends Worker {

    private static final String TAG = "CameraWorker";

    public CameraWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Log.d(TAG, "🌿 일일 자동 촬영 시작");

        ApiService api = ApiClient.getApiService();

        // 1. 전체 구역 목록 조회
        CountDownLatch fieldLatch = new CountDownLatch(1);
        final List<Field>[] fieldsHolder = new List[]{null};

        api.getFields().enqueue(new Callback<List<Field>>() {
            @Override
            public void onResponse(@NonNull Call<List<Field>> call,
                                   @NonNull Response<List<Field>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    fieldsHolder[0] = response.body();
                } else {
                    Log.e(TAG, "구역 조회 실패: " + response.code());
                }
                fieldLatch.countDown();
            }

            @Override
            public void onFailure(@NonNull Call<List<Field>> call, @NonNull Throwable t) {
                Log.e(TAG, "구역 조회 네트워크 오류: " + t.getMessage());
                fieldLatch.countDown();
            }
        });

        try {
            fieldLatch.await(15, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return Result.retry();
        }

        List<Field> fields = fieldsHolder[0];
        if (fields == null || fields.isEmpty()) {
            Log.e(TAG, "구역 목록을 가져오지 못했습니다. 재시도 예약.");
            return Result.retry();
        }

        Log.d(TAG, "촬영 대상 구역 수: " + fields.size());

        // 2. 각 구역에 대해 이미지 촬영 후 업로드
        for (Field field : fields) {
            Log.d(TAG, "구역 [" + field.name + "] 촬영 중...");
            File imageFile = captureImageForField(field.name);

            if (imageFile != null && imageFile.exists()) {
                boolean uploaded = uploadImage(api, field.id, imageFile);
                if (uploaded) {
                    Log.d(TAG, "✅ [" + field.name + "] 업로드 성공");
                } else {
                    Log.w(TAG, "⚠️ [" + field.name + "] 업로드 실패");
                }
                // 업로드 후 임시 파일 삭제
                //noinspection ResultOfMethodCallIgnored
                imageFile.delete();
            } else {
                Log.w(TAG, "⚠️ [" + field.name + "] 이미지 촬영 실패 — 스킵");
            }
        }

        Log.d(TAG, "🌿 일일 자동 촬영 완료");
        return Result.success();
    }

    /**
     * CameraX를 사용해 지정 구역 이미지를 촬영합니다.
     * Worker는 백그라운드 스레드에서 실행되므로 동기적으로 래치를 사용합니다.
     *
     * @param fieldName 구역 이름 (파일명에 포함)
     * @return 촬영된 이미지 파일, 실패 시 null
     */
    private File captureImageForField(String fieldName) {
        Context context = getApplicationContext();
        File outputFile = new File(
                context.getCacheDir(),
                "capture_" + fieldName + "_" + System.currentTimeMillis() + ".jpg"
        );

        CountDownLatch captureLatch = new CountDownLatch(1);
        AtomicBoolean success = new AtomicBoolean(false);

        // CameraX 는 메인 스레드에서 바인딩해야 합니다
        android.os.Handler mainHandler = new android.os.Handler(
                android.os.Looper.getMainLooper()
        );

        mainHandler.post(() -> {
            try {
                ProcessCameraProvider cameraProvider =
                        ProcessCameraProvider.getInstance(context).get(10, TimeUnit.SECONDS);

                ImageCapture imageCapture = new ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build();

                // 간이 LifecycleOwner — Worker 수명주기용
                SimpleLifecycleOwner lifecycleOwner = new SimpleLifecycleOwner();
                lifecycleOwner.start();

                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(
                        lifecycleOwner,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        imageCapture
                );

                ImageCapture.OutputFileOptions options =
                        new ImageCapture.OutputFileOptions.Builder(outputFile).build();

                imageCapture.takePicture(
                        options,
                        ContextCompat.getMainExecutor(context),
                        new ImageCapture.OnImageSavedCallback() {
                            @Override
                            public void onImageSaved(
                                    @NonNull ImageCapture.OutputFileResults results) {
                                success.set(true);
                                lifecycleOwner.stop();
                                cameraProvider.unbindAll();
                                captureLatch.countDown();
                            }

                            @Override
                            public void onError(@NonNull ImageCaptureException exception) {
                                Log.e(TAG, "촬영 오류 [" + fieldName + "]: "
                                        + exception.getMessage());
                                lifecycleOwner.stop();
                                cameraProvider.unbindAll();
                                captureLatch.countDown();
                            }
                        }
                );

            } catch (ExecutionException | InterruptedException
                     | java.util.concurrent.TimeoutException e) {
                Log.e(TAG, "카메라 프로바이더 오류: " + e.getMessage());
                captureLatch.countDown();
            }
        });

        try {
            captureLatch.await(20, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        return success.get() ? outputFile : null;
    }

    /**
     * 이미지 파일을 /analyze 엔드포인트에 업로드합니다.
     */
    private boolean uploadImage(ApiService api, String fieldId, File imageFile) {
        CountDownLatch latch = new CountDownLatch(1);
        AtomicBoolean result = new AtomicBoolean(false);

        RequestBody fieldIdBody = RequestBody.create(
                MediaType.parse("text/plain"), fieldId
        );
        RequestBody fileBody = RequestBody.create(
                MediaType.parse("image/jpeg"), imageFile
        );
        MultipartBody.Part filePart = MultipartBody.Part.createFormData(
                "file", imageFile.getName(), fileBody
        );

        api.analyze(fieldIdBody, filePart).enqueue(new Callback<AnalyzeResponse>() {
            @Override
            public void onResponse(@NonNull Call<AnalyzeResponse> call,
                                   @NonNull Response<AnalyzeResponse> response) {
                if (response.isSuccessful()) {
                    result.set(true);
                    if (response.body() != null) {
                        Log.d(TAG, "분석 결과: " + response.body().diseaseType
                                + " (" + response.body().confidence + ")");
                    }
                } else {
                    Log.e(TAG, "업로드 실패: " + response.code());
                }
                latch.countDown();
            }

            @Override
            public void onFailure(@NonNull Call<AnalyzeResponse> call, @NonNull Throwable t) {
                Log.e(TAG, "업로드 네트워크 오류: " + t.getMessage());
                latch.countDown();
            }
        });

        try {
            latch.await(30, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        return result.get();
    }

    // ── 간이 LifecycleOwner (Worker 내부용) ──────────────────────────────────────
    private static class SimpleLifecycleOwner implements LifecycleOwner {
        private final LifecycleRegistry registry;

        SimpleLifecycleOwner() {
            registry = new LifecycleRegistry(this);
        }

        void start() {
            registry.setCurrentState(Lifecycle.State.STARTED);
        }

        void stop() {
            registry.setCurrentState(Lifecycle.State.DESTROYED);
        }

        @NonNull
        @Override
        public Lifecycle getLifecycle() {
            return registry;
        }
    }
}
