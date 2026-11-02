package com.example.CRM.stock.service;

import com.example.CRM.stock.dto.StockUpsertRequest;
import com.example.CRM.stock.entity.StockEntity;

import java.util.List;

public interface StockService {
    StockEntity upsert(StockUpsertRequest req);
    List<StockEntity> listByWarehouse(Long warehouseId);
}
