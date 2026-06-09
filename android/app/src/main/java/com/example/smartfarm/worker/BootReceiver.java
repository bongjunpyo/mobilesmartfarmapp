package com.example.smartfarm.worker;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import java.util.Calendar;
import java.util.concurrent.TimeUnit;

/**
 * 기기 재부팅 후 WorkManager 일일 촬영 스케줄을 재등록합니다.
 *
 * AndroidManifest.xml 에 등록되어 BOOT_COMPLETED 인텐트를 수신합니다.
 * WorkManager는 기기 재부팅 시 자동 복구가 지원되지만, 명시적으로 등록해 두면
 * 초기 딜레이(다음 14:00까지 남은 시간)를 정확히 재계산할 수 있습니다.
 */
public class BootReceiver extends BroadcastReceiver {

    private static final String TAG = "BootReceiver";
    private static final String WORK_NAME = "daily_capture";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;

        String action = intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(action)
                || "android.intent.action.QUICKBOOT_POWERON".equals(action)) {

            Log.d(TAG, "📱 기기 재부팅 감지 — 일일 촬영 스케줄 재등록");
            scheduleDailyCapture(context);
        }
    }

    /**
     * 다음 14:00까지 남은 시간을 계산하여 24시간 주기 WorkManager 작업을 등록합니다.
     */
    private void scheduleDailyCapture(Context context) {
        Calendar now = Calendar.getInstance();
        Calendar target = Calendar.getInstance();
        target.set(Calendar.HOUR_OF_DAY, 14);
        target.set(Calendar.MINUTE, 0);
        target.set(Calendar.SECOND, 0);
        target.set(Calendar.MILLISECOND, 0);

        // 오늘 14:00이 이미 지났으면 내일 14:00으로 설정
        if (now.after(target)) {
            target.add(Calendar.DAY_OF_MONTH, 1);
        }

        long initialDelay = target.getTimeInMillis() - now.getTimeInMillis();
        long delayMinutes = TimeUnit.MILLISECONDS.toMinutes(initialDelay);
        Log.d(TAG, "다음 촬영까지 " + delayMinutes + "분 후 (" + target.getTime() + ")");

        PeriodicWorkRequest workRequest = new PeriodicWorkRequest.Builder(
                CameraWorker.class, 24, TimeUnit.HOURS)
                .setInitialDelay(initialDelay, TimeUnit.MILLISECONDS)
                .build();

        // KEEP: 이미 등록된 작업이 있으면 유지 (중복 방지)
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                workRequest
        );

        Log.d(TAG, "✅ 일일 촬영 스케줄 재등록 완료");
    }
}
