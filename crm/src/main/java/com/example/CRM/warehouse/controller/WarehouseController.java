package com.example.CRM.warehouse.controller;

import com.example.CRM.warehouse.dto.WarehouseRequest;
import com.example.CRM.warehouse.entity.WarehouseEntity;
import com.example.CRM.warehouse.service.WarehouseService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/warehouses")
@RequiredArgsConstructor
public class WarehouseController {

    private final WarehouseService service;

    @PostMapping
    public WarehouseEntity create(@Valid @RequestBody WarehouseRequest req) {
        return service.create(req);
    }

    @GetMapping
    public List<WarehouseEntity> list() {
        return service.list();
    }
}
