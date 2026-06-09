package com.example.smartfarm.network;

import com.example.smartfarm.model.AnalyzeResponse;
import com.example.smartfarm.model.Field;
import com.example.smartfarm.model.ImageItem;
import com.example.smartfarm.model.NotificationItem;

import java.util.List;

import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Multipart;
import retrofit2.http.PATCH;
import retrofit2.http.POST;
import retrofit2.http.Part;
import retrofit2.http.Path;
import retrofit2.http.Query;

public interface ApiService {

    // 전체 구역 목록 + 최신 분석 결과 (Farm 화면)
    @GET("fields")
    Call<List<Field>> getFields();

    // 이미지 분석 요청
    @Multipart
    @POST("analyze")
    Call<AnalyzeResponse> analyze(
            @Part("field_id") RequestBody fieldId,
            @Part MultipartBody.Part image
    );

    // 전체 이미지 목록 (Image 화면)
    @GET("images")
    Call<List<ImageItem>> getImages(
            @Query("field_id") String fieldId,
            @Query("limit") int limit,
            @Query("offset") int offset
    );

    // 알림 목록 조회
    @GET("notifications")
    Call<List<NotificationItem>> getNotifications();

    // 알림 읽음 처리
    @PATCH("notifications/{id}/read")
    Call<Void> markNotificationRead(@Path("id") String notificationId);
}
