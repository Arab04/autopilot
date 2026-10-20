package com.example.CRM.settings.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "settings")
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor @Builder
public class SettingsEntity {

    @Id
    private Long id; // always 1

    private String companyName;
    private String address;
    private String phone;
    private String inn;

    private String baseCurrency; // UZS
    private double usdRate; // 12650 demo
    private boolean autoRate;

    private double taxPercent; // QQS 12

    // notifications for credit
    private boolean smsEnabled;
    private boolean telegramEnabled;
    private int remindDaysBefore;
    private String remindTemplate;
    private String overdueTemplate;
}
