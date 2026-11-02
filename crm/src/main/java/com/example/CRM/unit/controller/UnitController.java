package com.example.CRM.unit.controller;

import com.example.CRM.unit.entity.UnitEntity;
import com.example.CRM.unit.dto.UnitCreateRequest;
import com.example.CRM.unit.service.UnitService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/units")
@RequiredArgsConstructor
public class UnitController {

    private final UnitService service;

    @PostMapping
    public UnitEntity create(@Valid @RequestBody UnitCreateRequest req) {
        return service.create(req);
    }

    @GetMapping
    public List<UnitEntity> list(@RequestParam(required = false) String category) {
        return service.list(category);
    }

    @PutMapping("/{id}")
    public UnitEntity update(@PathVariable Long id, @Valid @RequestBody UnitCreateRequest req) {
        return service.update(id, req);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}