package com.example.CRM.sale.dto;

import jakarta.validation.constraints.NotNull;

import java.util.List;

public record CheckoutRequest(
        @NotNull Long warehouseId,
        String customerName,
        String customerPhone,
        @NotNull String paymentType, // CASH or CREDIT
        @NotNull List<CheckoutItem> items
) {
    public record CheckoutItem(@NotNull Long productId, double quantity) {}
}