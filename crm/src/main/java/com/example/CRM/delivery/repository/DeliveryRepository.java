package com.example.CRM.delivery.repository;

import com.example.CRM.delivery.entity.DeliveryEntity;
import com.example.CRM.delivery.entity.DeliveryStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;

public interface DeliveryRepository extends JpaRepository<DeliveryEntity, Long> {
    List<DeliveryEntity> findByStatusIn(Collection<DeliveryStatus> statuses);

    List<DeliveryEntity> findAllByOrderByIdDesc();
}
