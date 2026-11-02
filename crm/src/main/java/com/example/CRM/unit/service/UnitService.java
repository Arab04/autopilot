package com.example.CRM.unit.service;

import com.example.CRM.unit.entity.UnitEntity;
import com.example.CRM.unit.dto.UnitCreateRequest;

import java.util.List;

public interface UnitService {
    UnitEntity create(UnitCreateRequest req);
    List<UnitEntity> list(String category);
    UnitEntity update(Long id, UnitCreateRequest req);
    void delete(Long id);
}
