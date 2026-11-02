package com.example.CRM.credit.entity;


import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "credits")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CreditEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long saleId;

    @Column(nullable = false)
    private String customerName;

    @Column(nullable = false)
    private String phone;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal totalAmount;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal paidAmount;

    @Column(nullable = false)
    private LocalDate dueDate;

    @Column(nullable = false, length = 20)
    private String status; // OPEN, CLOSED
}
