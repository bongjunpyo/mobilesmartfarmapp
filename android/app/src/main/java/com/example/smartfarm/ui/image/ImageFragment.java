package com.example.smartfarm.ui.image;

import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.bumptech.glide.Glide;
import com.example.smartfarm.R;
import com.example.smartfarm.model.Field;
import com.example.smartfarm.model.ImageItem;
import com.example.smartfarm.network.ApiClient;
import com.example.smartfarm.repository.PlantRepository;
import com.google.android.material.bottomsheet.BottomSheetDialog;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class ImageFragment extends Fragment {

    private RecyclerView rvImages;
    private SwipeRefreshLayout swipeRefresh;
    private ImageAdapter adapter;
    private final List<ImageItem> imageList = new ArrayList<>();
    private final PlantRepository repository = new PlantRepository();

    private TextView badgeTotal, badgeDiseased;
    private TextView btnNotification, tvNotifBadge;
    private ProgressBar progressBar;
    private LinearLayout filterChipGroup;

    private String selectedFieldId = null; // null = 전체

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_image, container, false);

        rvImages      = view.findViewById(R.id.rv_images);
        swipeRefresh  = view.findViewById(R.id.swipe_refresh);
        badgeTotal    = view.findViewById(R.id.badge_total);
        badgeDiseased = view.findViewById(R.id.badge_diseased);
        progressBar     = view.findViewById(R.id.progress_bar);
        filterChipGroup = view.findViewById(R.id.filter_chip_group);
        btnNotification = view.findViewById(R.id.btn_notification);
        tvNotifBadge    = view.findViewById(R.id.tv_notif_badge);

        btnNotification.setOnClickListener(v -> openNotification());
        loadNotifBadge();

        rvImages.setLayoutManager(new GridLayoutManager(getContext(), 2));
        adapter = new ImageAdapter(getContext(), imageList, this::showImageDetail);
        rvImages.setAdapter(adapter);

        swipeRefresh.setColorSchemeColors(0xFF43A047);
        swipeRefresh.setOnRefreshListener(() -> loadImages(selectedFieldId));

        loadFilterChips();
        loadImages(null);

        return view;
    }

    // 구역 필터 칩 동적 생성
    private void loadFilterChips() {
        repository.getFields(new Callback<List<Field>>() {
            @Override
            public void onResponse(@NonNull Call<List<Field>> call,
                                   @NonNull Response<List<Field>> response) {
                if (!isAdded() || response.body() == null) return;

                // 전체 칩
                addChip("전체", null, true);

                for (Field field : response.body()) {
                    addChip(field.name.toUpperCase(), field.id, false);
                }
            }
            @Override
            public void onFailure(@NonNull Call<List<Field>> call, @NonNull Throwable t) {}
        });
    }

    private void addChip(String label, String fieldId, boolean selected) {
        if (getContext() == null) return;

        TextView chip = new TextView(getContext());
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(6, 0, 6, 0);
        chip.setLayoutParams(params);
        chip.setText(label);
        chip.setTextSize(12f);
        chip.setPadding(24, 12, 24, 12);
        chip.setTypeface(null, selected ? Typeface.BOLD : Typeface.NORMAL);
        applyChipStyle(chip, selected);

        chip.setOnClickListener(v -> {
            selectedFieldId = fieldId;
            // 모든 칩 스타일 초기화
            for (int i = 0; i < filterChipGroup.getChildCount(); i++) {
                applyChipStyle((TextView) filterChipGroup.getChildAt(i), false);
                ((TextView) filterChipGroup.getChildAt(i)).setTypeface(null, Typeface.NORMAL);
            }
            applyChipStyle(chip, true);
            chip.setTypeface(null, Typeface.BOLD);
            loadImages(fieldId);
        });

        filterChipGroup.addView(chip);
    }

    private void applyChipStyle(TextView chip, boolean selected) {
        if (selected) {
            chip.setBackgroundColor(Color.parseColor("#43A047"));
            chip.setTextColor(Color.WHITE);
        } else {
            chip.setBackgroundColor(Color.parseColor("#EEEEEE"));
            chip.setTextColor(Color.parseColor("#555555"));
        }
        // 둥근 모서리는 배경으로 별도 처리하기 어려워 배경색으로 대체
    }

    private void loadImages(String fieldId) {
        if (imageList.isEmpty()) progressBar.setVisibility(View.VISIBLE);
        repository.getImages(fieldId, 50, 0, new Callback<List<ImageItem>>() {
            @Override
            public void onResponse(@NonNull Call<List<ImageItem>> call,
                                   @NonNull Response<List<ImageItem>> response) {
                if (!isAdded()) return;
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    imageList.clear();
                    imageList.addAll(response.body());
                    adapter.notifyDataSetChanged();
                    updateBadges();
                }
            }

            @Override
            public void onFailure(@NonNull Call<List<ImageItem>> call, @NonNull Throwable t) {
                if (!isAdded() || getContext() == null) return;
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
                Toast.makeText(getContext(), "서버 연결 실패: " + t.getMessage(),
                        Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void updateBadges() {
        int diseased = 0;
        for (ImageItem item : imageList) {
            if (item.isDiseased()) diseased++;
        }
        badgeTotal.setText("전체 " + imageList.size());
        badgeDiseased.setText("질병 " + diseased);
    }

    private void openNotification() {
        requireActivity().getSupportFragmentManager()
                .beginTransaction()
                .replace(R.id.fragment_container,
                        new com.example.smartfarm.ui.notification.NotificationFragment())
                .addToBackStack(null)
                .commit();
    }

    private void loadNotifBadge() {
        repository.getNotifications(new Callback<List<com.example.smartfarm.model.NotificationItem>>() {
            @Override
            public void onResponse(@NonNull Call<List<com.example.smartfarm.model.NotificationItem>> call,
                                   @NonNull Response<List<com.example.smartfarm.model.NotificationItem>> response) {
                if (!isAdded() || response.body() == null) return;
                long unread = response.body().stream().filter(n -> !n.isRead).count();
                if (unread > 0) {
                    tvNotifBadge.setVisibility(View.VISIBLE);
                    tvNotifBadge.setText(String.valueOf(unread));
                } else {
                    tvNotifBadge.setVisibility(View.GONE);
                }
            }
            @Override
            public void onFailure(@NonNull Call<List<com.example.smartfarm.model.NotificationItem>> call,
                                  @NonNull Throwable t) {}
        });
    }

    private void showImageDetail(ImageItem item) {
        if (getContext() == null) return;

        BottomSheetDialog dialog = new BottomSheetDialog(getContext());
        View sheetView = LayoutInflater.from(getContext())
                .inflate(R.layout.bottom_sheet_image_detail, null);

        ImageView ivImage     = sheetView.findViewById(R.id.iv_detail_image);
        TextView tvFieldName  = sheetView.findViewById(R.id.tv_detail_field);
        TextView tvDate       = sheetView.findViewById(R.id.tv_detail_date);
        TextView tvDisease    = sheetView.findViewById(R.id.tv_detail_disease);
        TextView tvConfidence = sheetView.findViewById(R.id.tv_detail_confidence);

        tvFieldName.setText("구역: " + item.fieldName.toUpperCase());
        tvDate.setText("촬영: " + (item.capturedAt != null
                ? item.capturedAt.substring(0, 19).replace("T", " ") : ""));

        if (item.isDiseased()) {
            tvDisease.setText("질병: " + item.diseaseType);
            tvConfidence.setText(item.confidence != null
                    ? String.format("신뢰도: %.0f%%", item.confidence * 100) : "");
        } else {
            tvDisease.setText("상태: 정상");
            tvConfidence.setVisibility(View.GONE);
        }

        String imageUrl = ApiClient.BASE_URL + item.filePath.replaceFirst("^/", "");
        Glide.with(getContext()).load(imageUrl).into(ivImage);

        dialog.setContentView(sheetView);
        dialog.show();
    }
}
