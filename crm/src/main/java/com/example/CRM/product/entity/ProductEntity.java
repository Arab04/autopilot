package com.example.CRM.product.entity;

import com.example.CRM.unit.entity.UnitEntity;
import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;

@Entity
@Table(name = "products")
@Getter
@Setter
@NoArgsConstructor @AllArgsConstructor @Builder
public class ProductEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 120)
    private String name;

    @Column(length = 50)
    private String sku;

    @Column(length = 50)
    private String barcode;

    @Column(length = 60)
    private String brand;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal retailPrice;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal wholesalePrice;

    @Column(nullable = false)
    private int minQuantity;

    @Column(nullable = false)
    private boolean active;

    @ManyToOne(optional = false)
    @JoinColumn(name = "unit_id")
    private UnitEntity unit;
}
