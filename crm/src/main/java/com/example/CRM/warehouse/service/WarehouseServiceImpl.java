package com.example.CRM.warehouse.service;

import com.example.CRM.warehouse.dto.WarehouseRequest;
import com.example.CRM.warehouse.entity.WarehouseEntity;
import com.example.CRM.warehouse.repository.WarehouseRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class WarehouseServiceImpl implements WarehouseService {

    private final WarehouseRepository repo;

    @Override
    public WarehouseEntity create(WarehouseRequest req) {
        return repo.save(WarehouseEntity.builder().name(req.name()).address(req.address()).build());
    }

    @Override
    public List<WarehouseEntity> list() {
        return repo.findAll();
    }
}
