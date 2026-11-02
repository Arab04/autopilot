package com.example.CRM.product.service;

import com.example.CRM.product.dto.ProductRequest;
import com.example.CRM.product.entity.ProductEntity;

import java.util.List;

public interface ProductService {
    ProductEntity create(ProductRequest req);
    ProductEntity update(Long id, ProductRequest req);
    List<ProductEntity> list();
    List<ProductEntity> search(String q);
    void delete(Long id);
}