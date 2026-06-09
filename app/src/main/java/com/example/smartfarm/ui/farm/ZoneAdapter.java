package com.example.smartfarm.ui.farm;

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
import com.example.smartfarm.model.Field;
import com.example.smartfarm.network.ApiClient;
import com.google.android.material.card.MaterialCardView;
import java.util.List;

public class ZoneAdapter extends RecyclerView.Adapter<ZoneAdapter.ViewHolder> {

    public interface OnZoneClickListener {
        void onZoneClick(Field field);
    }

    private final Context context;
    private final List<Field> fields;
    private final OnZoneClickListener listener;

    public ZoneAdapter(Context context, List<Field> fields, OnZoneClickListener listener) {
        this.context  = context;
        this.fields   = fields;
        this.listener = listener;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context).inflate(R.layout.item_zone, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        Field field = fields.get(position);

        holder.tvZoneName.setText(field.name.toUpperCase());

        MaterialCardView card = (MaterialCardView) holder.itemView;

        switch (field.status) {
            case "DANGER":
                // 빨간 테두리
                card.setStrokeWidth(dpToPx(2));
                card.setStrokeColor(Color.parseColor("#EF5350"));
                card.setCardBackgroundColor(Color.WHITE);

                holder.tvZoneStatus.setText("⚠ 위험");
                holder.tvZoneStatus.setTextColor(Color.parseColor("#C62828"));

                holder.ivWarning.setVisibility(View.VISIBLE);
                holder.ivWarning.setColorFilter(Color.parseColor("#C62828"));

                if (field.latestAnalysis != null) {
                    holder.tvDiseaseBadge.setVisibility(View.VISIBLE);
                    holder.tvDiseaseBadge.setText(field.latestAnalysis.diseaseType);
                    holder.tvDiseaseBadge.setBackgroundResource(R.drawable.badge_danger);
                }
                break;

            case "WARNING":
                // 주황 테두리
                card.setStrokeWidth(dpToPx(2));
                card.setStrokeColor(Color.parseColor("#FFA726"));
                card.setCardBackgroundColor(Color.WHITE);

                holder.tvZoneStatus.setText("! 주의");
                holder.tvZoneStatus.setTextColor(Color.parseColor("#E65100"));

                holder.ivWarning.setVisibility(View.VISIBLE);
                holder.ivWarning.setColorFilter(Color.parseColor("#E65100"));

                if (field.latestAnalysis != null) {
                    holder.tvDiseaseBadge.setVisibility(View.VISIBLE);
                    holder.tvDiseaseBadge.setText(field.latestAnalysis.diseaseType);
                    holder.tvDiseaseBadge.setBackgroundResource(R.drawable.badge_warning);
                }
                break;

            default:
                // 테두리 없음
                card.setStrokeWidth(dpToPx(1));
                card.setStrokeColor(Color.parseColor("#EEEEEE"));
                card.setCardBackgroundColor(Color.WHITE);

                holder.tvZoneStatus.setText("✓ 정상");
                holder.tvZoneStatus.setTextColor(Color.parseColor("#43A047"));

                holder.ivWarning.setVisibility(View.GONE);
                holder.tvDiseaseBadge.setVisibility(View.GONE);
                break;
        }

        // 신뢰도 표시
        if (field.latestAnalysis != null && !"NORMAL".equals(field.latestAnalysis.diseaseType)) {
            holder.tvConfidence.setVisibility(View.VISIBLE);
            holder.tvConfidence.setText(
                    String.format("신뢰도 %.0f%%", field.latestAnalysis.confidence * 100));
        } else {
            holder.tvConfidence.setVisibility(View.GONE);
        }

        // 이미지 로딩
        if (field.latestAnalysis != null && field.latestAnalysis.imagePath != null) {
            String imageUrl = ApiClient.BASE_URL +
                    field.latestAnalysis.imagePath.replaceFirst("^/", "");
            Glide.with(context).load(imageUrl).centerCrop()
                    .placeholder(android.R.color.darker_gray)
                    .into(holder.ivZoneImage);
        } else {
            holder.ivZoneImage.setImageDrawable(null);
            holder.ivZoneImage.setBackgroundColor(Color.parseColor("#F1F8E9"));
        }

        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onZoneClick(field);
        });
    }

    private int dpToPx(int dp) {
        return (int) (dp * context.getResources().getDisplayMetrics().density);
    }

    @Override
    public int getItemCount() { return fields.size(); }

    static class ViewHolder extends RecyclerView.ViewHolder {
        MaterialCardView cardView;
        ImageView ivZoneImage, ivWarning;
        TextView tvZoneName, tvZoneStatus, tvDiseaseBadge, tvConfidence;

        ViewHolder(@NonNull View itemView) {
            super(itemView);
            cardView      = (MaterialCardView) itemView;
            ivZoneImage   = itemView.findViewById(R.id.iv_zone_image);
            ivWarning     = itemView.findViewById(R.id.iv_warning);
            tvZoneName    = itemView.findViewById(R.id.tv_zone_name);
            tvZoneStatus  = itemView.findViewById(R.id.tv_zone_status);
            tvDiseaseBadge = itemView.findViewById(R.id.tv_disease_badge);
            tvConfidence  = itemView.findViewById(R.id.tv_confidence);
        }
    }
}
