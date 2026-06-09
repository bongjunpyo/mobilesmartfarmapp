package com.example.smartfarm.model;

import com.google.gson.annotations.SerializedName;

public class NotificationItem {
    @SerializedName("id")
    public String id;

    @SerializedName("field_id")
    public String fieldId;

    @SerializedName("message")
    public String message;

    @SerializedName("is_read")
    public boolean isRead;

    @SerializedName("created_at")
    public String createdAt;
}
