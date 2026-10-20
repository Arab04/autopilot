package com.example.CRM.stock.entity;

import com.example.CRM.product.entity.ProductEntity;
import com.example.CRM.warehouse.entity.WarehouseEntity;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "stocks",
        uniqueConstraints = @UniqueConstraint(columnNames = {"product_id", "warehouse_id"})
)
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor @Builder
public class StockEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(optional = false) @JoinColumn(name = "product_id")
    private ProductEntity product;

    @ManyToOne(optional = false) @JoinColumn(name = "warehouse_id")
    private WarehouseEntity warehouse;

    @Column(nullable = false)
    private double quantity;
}
