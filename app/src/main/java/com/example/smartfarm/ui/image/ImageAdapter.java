package com.example.smartfarm.ui.image;

import android.content.Context;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.bumptech.glide.Glide;
import com.example.smartfarm.R;
import com.example.smartfarm.model.ImageItem;
import com.example.smartfarm.network.ApiClient;
import com.google.android.material.card.MaterialCardView;
import java.util.List;

public class ImageAdapter extends RecyclerView.Adapter<ImageAdapter.ViewHolder> {

    public interface OnImageClickListener {
        void onImageClick(ImageItem item);
    }

    private final Context context;
    private final List<ImageItem> images;
    private final OnImageClickListener listener;

    public ImageAdapter(Context context, List<ImageItem> images, OnImageClickListener listener) {
        this.context  = context;
        this.images   = images;
        this.listener = listener;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context).inflate(R.layout.item_image, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        ImageItem item = images.get(position);

        MaterialCardView card = (MaterialCardView) holder.itemView;

        // 구역명
        holder.tvFieldName.setText(item.fieldName != null
                ? item.fieldName.toUpperCase() : "");

        // 날짜
        String date = "";
        if (item.capturedAt != null && item.capturedAt.length() >= 16) {
            date = item.capturedAt.substring(0, 16).replace("T", "  ");
        }
        holder.tvDate.setText(date);

        // 질병 여부에 따라 카드 스타일 분기
        if (item.isDiseased()) {
            // 빨간 테두리
            card.setStrokeWidth(dpToPx(2));
            card.setStrokeColor(Color.parseColor("#EF5350"));

            // 질병 배지
            holder.tvDiseaseBadge.setVisibility(View.VISIBLE);
            holder.tvDiseaseBadge.setText(item.diseaseType);

            // 상태 레이블
            holder.tvStatusLabel.setText("⚠ " + item.diseaseType);
            holder.tvStatusLabel.setTextColor(Color.parseColor("#C62828"));

            // 신뢰도
            if (item.confidence != null) {
                holder.tvConfidence.setVisibility(View.VISIBLE);
                holder.tvConfidence.setText(
                        String.format("%.0f%%", item.confidence * 100));
            } else {
                holder.tvConfidence.setVisibility(View.GONE);
            }
        } else {
            // 테두리 없음
            card.setStrokeWidth(dpToPx(1));
            card.setStrokeColor(Color.parseColor("#EEEEEE"));

            holder.tvDiseaseBadge.setVisibility(View.GONE);
            holder.tvStatusLabel.setText("✓ 정상");
            holder.tvStatusLabel.setTextColor(Color.parseColor("#43A047"));
            holder.tvConfidence.setVisibility(View.GONE);
        }

        // 이미지 로딩
        String imageUrl = ApiClient.BASE_URL + item.filePath.replaceFirst("^/", "");
        Glide.with(context)
                .load(imageUrl)
                .centerCrop()
                .placeholder(android.R.color.darker_gray)
                .into(holder.ivThumbnail);

        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onImageClick(item);
        });
    }

    private int dpToPx(int dp) {
        return (int) (dp * context.getResources().getDisplayMetrics().density);
    }

    @Override
    public int getItemCount() { return images.size(); }

    static class ViewHolder extends RecyclerView.ViewHolder {
        MaterialCardView cardView;
        ImageView ivThumbnail;
        TextView tvFieldName, tvDate, tvDiseaseBadge, tvStatusLabel, tvConfidence;

        ViewHolder(@NonNull View itemView) {
            super(itemView);
            cardView       = (MaterialCardView) itemView;
            ivThumbnail    = itemView.findViewById(R.id.iv_thumbnail);
            tvFieldName    = itemView.findViewById(R.id.tv_field_name);
            tvDate         = itemView.findViewById(R.id.tv_date);
            tvDiseaseBadge = itemView.findViewById(R.id.tv_disease_badge);
            tvStatusLabel  = itemView.findViewById(R.id.tv_status_label);
            tvConfidence   = itemView.findViewById(R.id.tv_confidence);
        }
    }
}
