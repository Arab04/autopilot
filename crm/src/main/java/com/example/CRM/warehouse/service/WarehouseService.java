package com.example.CRM.warehouse.service;

import com.example.CRM.warehouse.dto.WarehouseRequest;
import com.example.CRM.warehouse.entity.WarehouseEntity;

import java.util.List;

public interface WarehouseService {
    WarehouseEntity create(WarehouseRequest req);
    List<WarehouseEntity> list();
}
