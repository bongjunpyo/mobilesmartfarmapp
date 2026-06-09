package com.example.smartfarm.model;

import com.google.gson.annotations.SerializedName;

public class ImageItem {
    @SerializedName("id")
    public String id;

    @SerializedName("field_id")
    public String fieldId;

    @SerializedName("field_name")
    public String fieldName;     // a1, b1 ...

    @SerializedName("file_path")
    public String filePath;

    @SerializedName("file_size_kb")
    public Integer fileSizeKb;

    @SerializedName("captured_at")
    public String capturedAt;

    @SerializedName("disease_type")
    public String diseaseType;

    @SerializedName("confidence")
    public Float confidence;

    public boolean isDiseased() {
        return diseaseType != null && !diseaseType.equals("NORMAL");
    }
}
