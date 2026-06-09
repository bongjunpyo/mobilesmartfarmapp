package com.example.smartfarm.ui.notification;

import android.content.Context;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.example.smartfarm.R;
import com.example.smartfarm.model.NotificationItem;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class NotificationAdapter extends RecyclerView.Adapter<NotificationAdapter.ViewHolder> {

    public interface OnReadListener {
        void onRead(NotificationItem item);
    }

    private final Context context;
    private final List<NotificationItem> items;
    private final OnReadListener listener;

    // 메시지 파싱: "[A2] RUST 감지됨 (신뢰도: 92%)"
    private static final Pattern MSG_PATTERN =
            Pattern.compile("\\[([^]]+)]\\s+(\\S+)\\s+감지됨\\s+\\(신뢰도:\\s*([^)]+)\\)");

    public NotificationAdapter(Context context, List<NotificationItem> items,
                               OnReadListener listener) {
        this.context  = context;
        this.items    = items;
        this.listener = listener;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context)
                .inflate(R.layout.item_notification, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        NotificationItem item = items.get(position);

        // 메시지 파싱
        Matcher m = item.message != null ? MSG_PATTERN.matcher(item.message) : null;
        if (m != null && m.find()) {
            String field      = m.group(1); // "A2"
            String disease    = m.group(2); // "RUST"
            String confidence = m.group(3); // "92%"

            holder.tvFieldTag.setVisibility(View.VISIBLE);
            holder.tvFieldTag.setText(field);

            holder.tvDiseaseName.setVisibility(View.VISIBLE);
            holder.tvDiseaseName.setText(disease + " 감지");

            holder.tvConfidenceTag.setVisibility(View.VISIBLE);
            holder.tvConfidenceTag.setText("신뢰도 " + confidence);

            holder.tvMessage.setText(item.message);
        } else {
            holder.tvFieldTag.setVisibility(View.GONE);
            holder.tvDiseaseName.setVisibility(View.GONE);
            holder.tvConfidenceTag.setVisibility(View.GONE);
            holder.tvMessage.setText(item.message);
        }

        // 시간
        String time = item.createdAt != null && item.createdAt.length() >= 16
                ? item.createdAt.substring(0, 16).replace("T", " ")
                : "";
        holder.tvTime.setText(time);

        // 읽음/안읽음 스타일
        if (item.isRead) {
            holder.viewDot.setBackgroundColor(Color.parseColor("#DDDDDD"));
            holder.itemView.setAlpha(0.5f);
        } else {
            holder.viewDot.setBackgroundResource(R.drawable.badge_danger);
            holder.itemView.setAlpha(1.0f);
        }

        // 탭 → 읽음 처리
        holder.itemView.setOnClickListener(v -> {
            if (!item.isRead && listener != null) listener.onRead(item);
        });
    }

    @Override
    public int getItemCount() { return items.size(); }

    static class ViewHolder extends RecyclerView.ViewHolder {
        View viewDot;
        TextView tvFieldTag, tvDiseaseName, tvConfidenceTag, tvMessage, tvTime;

        ViewHolder(@NonNull View itemView) {
            super(itemView);
            viewDot         = itemView.findViewById(R.id.view_unread_dot);
            tvFieldTag      = itemView.findViewById(R.id.tv_field_tag);
            tvDiseaseName   = itemView.findViewById(R.id.tv_disease_name);
            tvConfidenceTag = itemView.findViewById(R.id.tv_confidence_tag);
            tvMessage       = itemView.findViewById(R.id.tv_notification_message);
            tvTime          = itemView.findViewById(R.id.tv_notification_time);
        }
    }
}
