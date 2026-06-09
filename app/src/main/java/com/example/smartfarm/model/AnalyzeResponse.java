package com.example.smartfarm.model;

import com.google.gson.annotations.SerializedName;

public class AnalyzeResponse {
    @SerializedName("id")
    public String id;

    @SerializedName("field_id")
    public String fieldId;

    @SerializedName("disease_type")
    public String diseaseType;

    @SerializedName("confidence")
    public float confidence;

    @SerializedName("analyzed_at")
    public String analyzedAt;

    @SerializedName("notification_sent")
    public boolean notificationSent;
}
