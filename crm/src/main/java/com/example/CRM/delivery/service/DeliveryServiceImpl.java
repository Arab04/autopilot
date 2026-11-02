package com.example.CRM.delivery.service;

import com.example.CRM.delivery.dto.DeliveryRequest;
import com.example.CRM.delivery.entity.DeliveryEntity;
import com.example.CRM.delivery.entity.DeliveryStatus;
import com.example.CRM.delivery.fleet.FleetClient;
import com.example.CRM.delivery.fleet.FleetException;
import com.example.CRM.delivery.fleet.FleetOrder;
import com.example.CRM.delivery.repository.DeliveryRepository;
import com.example.CRM.sale.entity.SaleEntity;
import com.example.CRM.sale.repository.SaleRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.EnumSet;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeliveryServiceImpl implements DeliveryService {

    private final DeliveryRepository repo;
    private final SaleRepository sales;
    private final FleetClient fleet;

    @Override
    public DeliveryEntity create(DeliveryRequest req) {
        String name = blankToNull(req.customerName());
        String phone = blankToNull(req.customerPhone());
        if (req.saleId() != null) {
            SaleEntity s = sales.findById(req.saleId())
                    .orElseThrow(() -> new EntityNotFoundException("Savdo topilmadi: " + req.saleId()));
            if (name == null) name = blankToNull(s.getCustomerName());
            if (phone == null) phone = blankToNull(s.getCustomerPhone());
        }
        if (name == null || phone == null) {
            throw new IllegalArgumentException("Mijoz ismi va telefoni kerak (yoki ular yozilgan savdo saleId)");
        }
        LocalDateTime now = LocalDateTime.now();
        DeliveryEntity d = repo.save(DeliveryEntity.builder()
                .saleId(req.saleId()).customerName(name).customerPhone(phone)
                .address(req.address()).lat(req.lat()).lon(req.lon()).note(blankToNull(req.note()))
                .status(DeliveryStatus.NEW).createdAt(now).updatedAt(now).build());
        return send(d);
    }

    /** Flotga yuboradi. Flot rad etsa yoki ulanib bo'lmasa, yetkazish FAILED bo'lib saqlanadi (keyin refresh). */
    private DeliveryEntity send(DeliveryEntity d) {
        try {
            FleetOrder o = fleet.create(d);
            d.setFleetOrderId(o.id());
            d.setPin(o.pin());
            d.setTrackingLink(o.trackingLink());
            d.setError(null);
            apply(d, o);
        } catch (FleetException e) {
            d.setStatus(DeliveryStatus.FAILED);
            d.setError(truncate(e.getMessage(), 300));
            d.setUpdatedAt(LocalDateTime.now());
        }
        return repo.save(d);
    }

    private void apply(DeliveryEntity d, FleetOrder o) {
        DeliveryStatus s = DeliveryStatus.fromFleet(o.holat());
        d.setStatus(s);
        d.setScooterId(o.skuter());
        d.setEtaMinutes(s.isActive() ? o.etaMinutes() : null);
        if (s == DeliveryStatus.DELIVERED && d.getDeliveredAt() == null) d.setDeliveredAt(LocalDateTime.now());
        d.setUpdatedAt(LocalDateTime.now());
    }

    @Override
    public List<DeliveryEntity> list() {
        return repo.findAllByOrderByIdDesc();
    }

    @Override
    public DeliveryEntity get(Long id) {
        return repo.findById(id).orElseThrow(() -> new EntityNotFoundException("Yetkazish topilmadi: " + id));
    }

    @Override
    public DeliveryEntity refresh(Long id) {
        DeliveryEntity d = get(id);
        if (d.getStatus() == DeliveryStatus.FAILED || d.getStatus() == DeliveryStatus.NEW) {
            return send(d);
        }
        if (!d.getStatus().isActive()) return d;
        apply(d, fleet.get(d.getFleetOrderId()));
        return repo.save(d);
    }

    @Override
    public int syncActive() {
        int n = 0;
        for (DeliveryEntity d : repo.findByStatusIn(EnumSet.of(DeliveryStatus.QUEUED, DeliveryStatus.ASSIGNED,
                DeliveryStatus.ON_THE_WAY, DeliveryStatus.ARRIVED))) {
            try {
                apply(d, fleet.get(d.getFleetOrderId()));
                repo.save(d);
                n++;
            } catch (FleetException | IllegalArgumentException e) {
                log.warn("Yetkazish {} holatini yangilab bo'lmadi: {}", d.getId(), e.getMessage());
            }
        }
        return n;
    }

    private static String blankToNull(String s) {
        return s == null || s.isBlank() ? null : s.trim();
    }

    private static String truncate(String s, int max) {
        return s == null || s.length() <= max ? s : s.substring(0, max);
    }
}
