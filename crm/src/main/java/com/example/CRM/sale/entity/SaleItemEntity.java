package com.example.CRM.sale.entity;

import com.example.CRM.product.entity.ProductEntity;
import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;

@Entity
@Table(name = "sale_items")
@Getter
@Setter
@NoArgsConstructor @AllArgsConstructor @Builder
public class SaleItemEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(optional = false) @JoinColumn(name = "sale_id")
    private SaleEntity sale;

    @ManyToOne(optional = false) @JoinColumn(name = "product_id")
    private ProductEntity product;

    @Column(nullable = false)
    private double quantity;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal price;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal lineTotal;
}