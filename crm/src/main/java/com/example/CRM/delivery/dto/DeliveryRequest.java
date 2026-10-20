package com.example.CRM.delivery.dto;

import jakarta.validation.constraints.*;

/**
 * Yangi yetkazish. Manzil koordinatasi (lat/lon) bilan; saleId berilsa, mijoz ismi va telefoni
 * bo'sh qoldirilganda savdodan olinadi.
 */
public record DeliveryRequest(
        Long saleId,
        @Size(max = 80) String customerName,
        @Size(max = 30) String customerPhone,
        @NotBlank @Size(max = 200) String address,
        @NotNull @DecimalMin("-90") @DecimalMax("90") Double lat,
        @NotNull @DecimalMin("-180") @DecimalMax("180") Double lon,
        @Size(max = 200) String note
) {}
