package com.example.smartfarm.repository;

import com.example.smartfarm.model.AnalyzeResponse;
import com.example.smartfarm.model.Field;
import com.example.smartfarm.model.ImageItem;
import com.example.smartfarm.model.NotificationItem;
import com.example.smartfarm.network.ApiClient;
import com.example.smartfarm.network.ApiService;

import java.io.File;
import java.util.List;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Callback;

public class PlantRepository {
    private final ApiService api;

    public PlantRepository() {
        this.api = ApiClient.getService();
    }

    // 전체 구역 목록 조회 (Farm 화면)
    public void getFields(Callback<List<Field>> callback) {
        api.getFields().enqueue(callback);
    }

    // 이미지 업로드 및 분석 요청
    public void analyzeImage(String fieldId, File imageFile, Callback<AnalyzeResponse> callback) {
        RequestBody fieldIdBody = RequestBody.create(
                MediaType.parse("text/plain"), fieldId);

        RequestBody fileBody = RequestBody.create(
                MediaType.parse("image/jpeg"), imageFile);

        MultipartBody.Part imagePart = MultipartBody.Part.createFormData(
                "file", imageFile.getName(), fileBody);

        api.analyze(fieldIdBody, imagePart).enqueue(callback);
    }

    // 이미지 갤러리 조회 (Image 화면)
    public void getImages(String fieldId, int limit, int offset, Callback<List<ImageItem>> callback) {
        api.getImages(fieldId, limit, offset).enqueue(callback);
    }

    // 알림 목록 조회
    public void getNotifications(Callback<List<NotificationItem>> callback) {
        api.getNotifications().enqueue(callback);
    }

    // 알림 읽음 처리
    public void markNotificationRead(String notificationId, Callback<Void> callback) {
        api.markNotificationRead(notificationId).enqueue(callback);
    }
}
