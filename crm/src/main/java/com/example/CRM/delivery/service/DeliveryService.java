package com.example.CRM.delivery.service;

import com.example.CRM.delivery.dto.DeliveryRequest;
import com.example.CRM.delivery.entity.DeliveryEntity;

import java.util.List;

public interface DeliveryService {
    DeliveryEntity create(DeliveryRequest req);

    List<DeliveryEntity> list();

    DeliveryEntity get(Long id);

    /** Flotdan joriy holatni olib yangilaydi; FAILED bo'lsa, flotga qayta yuboradi. */
    DeliveryEntity refresh(Long id);

    /** Barcha faol yetkazishlar holatini flotdan yangilaydi (rejalashtirilgan). */
    int syncActive();
}
