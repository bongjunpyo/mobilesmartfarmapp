package com.example.smartfarm.model;

import com.google.gson.annotations.SerializedName;

public class Field {
    @SerializedName("id")
    public String id;

    @SerializedName("name")
    public String name;          // a1, b1, c1 ...

    @SerializedName("location")
    public String location;

    @SerializedName("status")
    public String status;        // NORMAL / WARNING / DANGER

    @SerializedName("created_at")
    public String createdAt;

    @SerializedName("latest_analysis")
    public LatestAnalysis latestAnalysis;

    public boolean isDangerous() {
        return "DANGER".equals(status) || "WARNING".equals(status);
    }
}
