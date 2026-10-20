package com.example.CRM.unit.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "units")
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor @Builder
public class UnitEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(nullable = false, length = 10)
    private String symbol;

    @Column(nullable = false)
    private String category; // OGIRLIK, DONA, MAYDON, HAJM

    @Column(nullable = false)
    private boolean mainUnit;

    @Column(nullable = false)
    private double coefficient; // derived -> main unit ga nisbatan
}