package com.example.CRM.delivery.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "deliveries")
@Getter
@Setter
@NoArgsConstructor @AllArgsConstructor @Builder
public class DeliveryEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long saleId;

    @Column(nullable = false, length = 80)
    private String customerName;

    @Column(nullable = false, length = 30)
    private String customerPhone;

    @Column(nullable = false, length = 200)
    private String address;

    @Column(nullable = false)
    private double lat;

    @Column(nullable = false)
    private double lon;

    @Column(length = 200)
    private String note;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private DeliveryStatus status;

    private Long fleetOrderId;   // flotdagi buyurtma raqami

    @Column(length = 10)
    private String pin;          // mijoz qutini shu PIN bilan ochadi

    @Column(length = 200)
    private String trackingLink; // mijoz Telegram botida kuzatish havolasi (bot yoqilgan bo'lsa)

    private Integer scooterId;

    private Double etaMinutes;   // flot hisoblagan yetib kelish vaqti

    @Column(length = 300)
    private String error;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    private LocalDateTime deliveredAt;
}
