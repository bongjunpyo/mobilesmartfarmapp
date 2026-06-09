package com.example.smartfarm.ui.farm;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
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
import com.example.smartfarm.network.ApiClient;
import com.example.smartfarm.repository.PlantRepository;
import com.google.android.material.bottomsheet.BottomSheetDialog;
import java.util.ArrayList;
import java.util.List;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class FarmFragment extends Fragment {

    private RecyclerView rvZones;
    private SwipeRefreshLayout swipeRefresh;
    private ZoneAdapter adapter;
    private final List<Field> fieldList = new ArrayList<>();
    private final PlantRepository repository = new PlantRepository();

    // 헤더 배지
    private TextView badgeNormal, badgeDanger, badgeWarning, tvLastUpdate;
    private TextView btnNotification, tvNotifBadge;
    private android.widget.ProgressBar progressBar;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_farm, container, false);

        rvZones      = view.findViewById(R.id.rv_zones);
        swipeRefresh = view.findViewById(R.id.swipe_refresh);
        badgeNormal  = view.findViewById(R.id.badge_normal);
        badgeDanger  = view.findViewById(R.id.badge_danger);
        badgeWarning = view.findViewById(R.id.badge_warning);
        tvLastUpdate = view.findViewById(R.id.tv_last_update);
        progressBar      = view.findViewById(R.id.progress_bar);
        btnNotification  = view.findViewById(R.id.btn_notification);
        tvNotifBadge     = view.findViewById(R.id.tv_notif_badge);

        btnNotification.setOnClickListener(v -> openNotification());
        loadNotifBadge();

        // 2열 그리드
        rvZones.setLayoutManager(new GridLayoutManager(getContext(), 2));
        adapter = new ZoneAdapter(getContext(), fieldList, this::showZoneDetail);
        rvZones.setAdapter(adapter);

        swipeRefresh.setColorSchemeColors(0xFF1B5E20);
        swipeRefresh.setOnRefreshListener(this::loadFields);
        loadFields();

        return view;
    }

    private void loadFields() {
        if (fieldList.isEmpty()) progressBar.setVisibility(View.VISIBLE);
        repository.getFields(new Callback<List<Field>>() {
            @Override
            public void onResponse(@NonNull Call<List<Field>> call,
                                   @NonNull Response<List<Field>> response) {
                if (!isAdded()) return;
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    fieldList.clear();
                    fieldList.addAll(response.body());
                    adapter.notifyDataSetChanged();
                    updateBadges();
                }
            }

            @Override
            public void onFailure(@NonNull Call<List<Field>> call, @NonNull Throwable t) {
                if (!isAdded() || getContext() == null) return;
                progressBar.setVisibility(View.GONE);
                swipeRefresh.setRefreshing(false);
                Toast.makeText(getContext(), "서버 연결 실패: " + t.getMessage(),
                        Toast.LENGTH_SHORT).show();
            }
        });
    }

    // 헤더 배지 카운트 업데이트
    private void updateBadges() {
        int normal = 0, danger = 0, warning = 0;
        String lastUpdate = null;

        for (Field f : fieldList) {
            switch (f.status) {
                case "DANGER":  danger++;  break;
                case "WARNING": warning++; break;
                default:        normal++;  break;
            }
            if (f.latestAnalysis != null && f.latestAnalysis.analyzedAt != null) {
                if (lastUpdate == null || f.latestAnalysis.analyzedAt.compareTo(lastUpdate) > 0) {
                    lastUpdate = f.latestAnalysis.analyzedAt;
                }
            }
        }

        badgeNormal.setText("정상 " + normal);
        badgeDanger.setText("위험 " + danger);
        badgeWarning.setText("주의 " + warning);

        if (lastUpdate != null && lastUpdate.length() >= 16) {
            tvLastUpdate.setText("마지막 촬영 " + lastUpdate.substring(0, 16).replace("T", " "));
        }
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
        new PlantRepository().getNotifications(new Callback<java.util.List<com.example.smartfarm.model.NotificationItem>>() {
            @Override
            public void onResponse(@NonNull Call<java.util.List<com.example.smartfarm.model.NotificationItem>> call,
                                   @NonNull Response<java.util.List<com.example.smartfarm.model.NotificationItem>> response) {
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
            public void onFailure(@NonNull Call<java.util.List<com.example.smartfarm.model.NotificationItem>> call,
                                  @NonNull Throwable t) {}
        });
    }

    // 구역 클릭 시 BottomSheet 팝업
    private void showZoneDetail(Field field) {
        if (getContext() == null) return;

        BottomSheetDialog dialog = new BottomSheetDialog(getContext());
        View sheetView = LayoutInflater.from(getContext())
                .inflate(R.layout.bottom_sheet_zone_detail, null);

        TextView tvTitle      = sheetView.findViewById(R.id.tv_detail_title);
        TextView tvStatus     = sheetView.findViewById(R.id.tv_detail_status);
        TextView tvDisease    = sheetView.findViewById(R.id.tv_detail_disease);
        TextView tvConfidence = sheetView.findViewById(R.id.tv_detail_confidence);
        TextView tvDate       = sheetView.findViewById(R.id.tv_detail_date);
        ImageView ivImage     = sheetView.findViewById(R.id.iv_detail_image);
        Button btnClose       = sheetView.findViewById(R.id.btn_close);

        tvTitle.setText("구역 " + field.name.toUpperCase());
        tvStatus.setText("상태: " + field.status);

        if (field.latestAnalysis != null) {
            tvDisease.setText("질병: " + field.latestAnalysis.diseaseType);
            tvConfidence.setText(
                    String.format("신뢰도: %.0f%%", field.latestAnalysis.confidence * 100));
            tvDate.setText("촬영: " + field.latestAnalysis.analyzedAt);

            if (field.latestAnalysis.imagePath != null) {
                String imageUrl = ApiClient.BASE_URL +
                        field.latestAnalysis.imagePath.replaceFirst("^/", "");
                Glide.with(getContext()).load(imageUrl).into(ivImage);
            }
        } else {
            tvDisease.setText("분석 기록 없음");
            tvConfidence.setVisibility(View.GONE);
            tvDate.setVisibility(View.GONE);
        }

        btnClose.setOnClickListener(v -> dialog.dismiss());
        dialog.setContentView(sheetView);
        dialog.show();
    }
}
