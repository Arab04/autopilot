package com.example.CRM.product.service;


import com.example.CRM.product.dto.ProductRequest;
import com.example.CRM.product.entity.ProductEntity;
import com.example.CRM.product.repository.ProductRepository;
import com.example.CRM.unit.entity.UnitEntity;
import com.example.CRM.unit.repository.UnitRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ProductServiceImpl implements ProductService {

    private final ProductRepository repo;
    private final UnitRepository unitRepo;

    @Override
    public ProductEntity create(ProductRequest req) {
        UnitEntity unit = unitRepo.findById(req.unitId())
                .orElseThrow(() -> new EntityNotFoundException("Unit not found"));

        ProductEntity p = ProductEntity.builder()
                .name(req.name())
                .sku(req.sku())
                .barcode(req.barcode())
                .brand(req.brand())
                .retailPrice(req.retailPrice())
                .wholesalePrice(req.wholesalePrice())
                .minQuantity(req.minQuantity())
                .active(req.active())
                .unit(unit)
                .build();

        return repo.save(p);
    }

    @Override
    public ProductEntity update(Long id, ProductRequest req) {
        ProductEntity p = repo.findById(id).orElseThrow(() -> new EntityNotFoundException("Product not found"));
        UnitEntity unit = unitRepo.findById(req.unitId()).orElseThrow(() -> new EntityNotFoundException("Unit not found"));

        p.setName(req.name());
        p.setSku(req.sku());
        p.setBarcode(req.barcode());
        p.setBrand(req.brand());
        p.setRetailPrice(req.retailPrice());
        p.setWholesalePrice(req.wholesalePrice());
        p.setMinQuantity(req.minQuantity());
        p.setActive(req.active());
        p.setUnit(unit);

        return repo.save(p);
    }

    @Override public List<ProductEntity> list() { return repo.findAll(); }

    @Override public List<ProductEntity> search(String q) { return repo.search(q); }

    @Override public void delete(Long id) { repo.deleteById(id); }
}
