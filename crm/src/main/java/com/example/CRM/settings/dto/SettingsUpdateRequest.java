package com.example.CRM.settings.dto;

public record SettingsUpdateRequest(
        String companyName,
        String address,
        String phone,
        String inn,
        String baseCurrency,
        Double usdRate,
        Boolean autoRate,
        Double taxPercent,
        Boolean smsEnabled,
        Boolean telegramEnabled,
        Integer remindDaysBefore,
        String remindTemplate,
        String overdueTemplate
) {}
