package com.example.CRM.product.repository;

import com.example.CRM.product.entity.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
@Repository
public interface ProductRepository extends JpaRepository<ProductEntity, Long> {

    @Query(value = """
    select * from products
    where (barcode = :q or sku = :q or cast(id as text) = :q)
    limit 20
  """, nativeQuery = true)
    List<ProductEntity> search(String q);
}
