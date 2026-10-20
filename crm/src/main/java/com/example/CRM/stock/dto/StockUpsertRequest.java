package com.example.CRM.stock.dto;

import jakarta.validation.constraints.NotNull;

public record StockUpsertRequest(
        @NotNull Long productId,
        @NotNull Long warehouseId,
        double quantity
) {}
