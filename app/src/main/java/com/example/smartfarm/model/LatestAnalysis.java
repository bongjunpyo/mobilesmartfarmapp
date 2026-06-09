package com.example.smartfarm.model;

import com.google.gson.annotations.SerializedName;

public class LatestAnalysis {
    @SerializedName("id")
    public String id;

    @SerializedName("disease_type")
    public String diseaseType;   // NORMAL / BLIGHT / RUST / MOSAIC / POWDERY_MILDEW / LEAF_SPOT

    @SerializedName("confidence")
    public float confidence;     // 0.0 ~ 1.0

    @SerializedName("analyzed_at")
    public String analyzedAt;

    @SerializedName("image_path")
    public String imagePath;

    public boolean isDiseased() {
        return diseaseType != null && !diseaseType.equals("NORMAL");
    }
}
