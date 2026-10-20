package com.example.CRM.sale.controller;


import com.example.CRM.sale.dto.CheckoutRequest;
import com.example.CRM.sale.entity.SaleEntity;
import com.example.CRM.sale.service.SaleService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/sales")
@RequiredArgsConstructor
public class SaleController {

    private final SaleService service;

    @PostMapping("/checkout")
    public SaleEntity checkout(@Valid @RequestBody CheckoutRequest req) {
        return service.checkout(req);
    }

    @GetMapping
    public List<SaleEntity> list() {
        return service.list();
    }
}