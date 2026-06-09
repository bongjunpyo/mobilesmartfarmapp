package com.example.smartfarm.ui.notification;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.DividerItemDecoration;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.example.smartfarm.R;
import com.example.smartfarm.model.NotificationItem;
import com.example.smartfarm.repository.PlantRepository;
import java.util.ArrayList;
import java.util.List;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class NotificationFragment extends Fragment {

    private RecyclerView rvNotifications;
    private SwipeRefreshLayout swipeRefresh;
    private TextView tvUnreadCount, tvMarkAllRead;
    private NotificationAdapter adapter;
    private final List<NotificationItem> notifList = new ArrayList<>();
    private final PlantRepository repository = new PlantRepository();

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container,
                             @Nullable Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_notification, container, false);

        rvNotifications = view.findViewById(R.id.rv_notifications);
        swipeRefresh    = view.findViewById(R.id.swipe_refresh);
        tvUnreadCount   = view.findViewById(R.id.tv_unread_count);
        tvMarkAllRead   = view.findViewById(R.id.tv_mark_all_read);
        view.findViewById(R.id.btn_back).setOnClickListener(
                v -> requireActivity().getSupportFragmentManager().popBackStack());

        rvNotifications.setLayoutManager(new LinearLayoutManager(getContext()));
        rvNotifications.addItemDecoration(
                new DividerItemDecoration(getContext(), DividerItemDecoration.VERTICAL));
        adapter = new NotificationAdapter(getContext(), notifList, this::markAsRead);
        rvNotifications.setAdapter(adapter);

        swipeRefresh.setColorSchemeColors(0xFF43A047);
        swipeRefresh.setOnRefreshListener(this::loadNotifications);

        tvMarkAllRead.setOnClickListener(v -> markAllRead());

        loadNotifications();
        return view;
    }

    private void loadNotifications() {
        repository.getNotifications(new Callback<List<NotificationItem>>() {
            @Override
            public void onResponse(@NonNull Call<List<NotificationItem>> call,
                                   @NonNull Response<List<NotificationItem>> response) {
                if (!isAdded()) return;
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    notifList.clear();
                    notifList.addAll(response.body());
                    adapter.notifyDataSetChanged();
                    updateUnreadCount();
                }
            }

            @Override
            public void onFailure(@NonNull Call<List<NotificationItem>> call, @NonNull Throwable t) {
                if (!isAdded() || getContext() == null) return;
                swipeRefresh.setRefreshing(false);
                Toast.makeText(getContext(), "서버 연결 실패", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void markAsRead(NotificationItem item) {
        repository.markNotificationRead(item.id, new Callback<Void>() {
            @Override
            public void onResponse(@NonNull Call<Void> call, @NonNull Response<Void> response) {
                if (!isAdded()) return;
                item.isRead = true;
                adapter.notifyDataSetChanged();
                updateUnreadCount();
            }
            @Override
            public void onFailure(@NonNull Call<Void> call, @NonNull Throwable t) {}
        });
    }

    private void markAllRead() {
        for (NotificationItem item : notifList) {
            if (!item.isRead) markAsRead(item);
        }
    }

    private void updateUnreadCount() {
        long unread = notifList.stream().filter(n -> !n.isRead).count();
        tvUnreadCount.setText(unread > 0
                ? "읽지 않은 알림 " + unread + "개"
                : "모든 알림을 확인했습니다");
    }
}
