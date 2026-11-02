package com.example.CRM.delivery.controller;

import com.example.CRM.delivery.dto.DeliveryRequest;
import com.example.CRM.delivery.entity.DeliveryEntity;
import com.example.CRM.delivery.service.DeliveryService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/** Skuter bilan yetkazish: CRM buyurtmani flotga beradi va holatini kuzatadi. */
@RestController
@RequestMapping("/api/deliveries")
@RequiredArgsConstructor
public class DeliveryController {

    private final DeliveryService service;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public DeliveryEntity create(@Valid @RequestBody DeliveryRequest req) {
        return service.create(req);
    }

    @GetMapping
    public List<DeliveryEntity> list() {
        return service.list();
    }

    @GetMapping("/{id}")
    public DeliveryEntity get(@PathVariable Long id) {
        return service.get(id);
    }

    @PostMapping("/{id}/refresh")
    public DeliveryEntity refresh(@PathVariable Long id) {
        return service.refresh(id);
    }
}
