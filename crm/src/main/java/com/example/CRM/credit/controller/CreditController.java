package com.example.CRM.credit.controller;

import com.example.CRM.credit.dto.CreditCreateRequest;
import com.example.CRM.credit.dto.CreditPayRequest;
import com.example.CRM.credit.entity.CreditEntity;
import com.example.CRM.credit.service.CreditService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/credits")
@RequiredArgsConstructor
public class CreditController {

    private final CreditService service;

    @PostMapping
    public CreditEntity create(@Valid @RequestBody CreditCreateRequest req) {
        return service.create(req);
    }

    @PostMapping("/{id}/pay")
    public CreditEntity pay(@PathVariable Long id, @Valid @RequestBody CreditPayRequest req) {
        return service.pay(id, req);
    }

    @GetMapping
    public List<CreditEntity> list() {
        return service.list();
    }
}