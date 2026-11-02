package com.example.CRM.settings.dto;

public record SettingsResponse(
        String companyName,
        String address,
        String phone,
        String inn,
        String baseCurrency,
        double usdRate,
        boolean autoRate,
        double taxPercent,
        boolean smsEnabled,
        boolean telegramEnabled,
        int remindDaysBefore,
        String remindTemplate,
        String overdueTemplate
) {}
