package com.example.CRM.product.controller;

import com.example.CRM.product.dto.ProductRequest;
import com.example.CRM.product.entity.ProductEntity;
import com.example.CRM.product.service.ProductService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductService service;

    @PostMapping
    public ProductEntity create(@Valid @RequestBody ProductRequest req) {
        return service.create(req);
    }

    @PutMapping("/{id}")
    public ProductEntity update(@PathVariable Long id, @Valid @RequestBody ProductRequest req) {
        return service.update(id, req);
    }

    @GetMapping
    public List<ProductEntity> list() {
        return service.list();
    }

    @GetMapping("/search")
    public List<ProductEntity> search(@RequestParam String q) {
        return service.search(q);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}

