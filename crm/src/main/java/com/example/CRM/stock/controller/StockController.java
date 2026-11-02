package com.example.CRM.stock.controller;

import com.example.CRM.stock.dto.StockUpsertRequest;
import com.example.CRM.stock.entity.StockEntity;
import com.example.CRM.stock.service.StockService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/stocks")
@RequiredArgsConstructor
public class StockController {

    private final StockService service;

    @PostMapping("/upsert")
    public StockEntity upsert(@Valid @RequestBody StockUpsertRequest req) {
        return service.upsert(req);
    }

    @GetMapping
    public List<StockEntity> listByWarehouse(@RequestParam Long warehouseId) {
        return service.listByWarehouse(warehouseId);
    }
}