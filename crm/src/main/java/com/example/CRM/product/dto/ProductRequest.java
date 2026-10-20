package com.example.CRM.product.dto;

import jakarta.validation.constraints.*;

import java.math.BigDecimal;

public record ProductRequest(
        @NotBlank String name,
        String sku,
        String barcode,
        String brand,
        @NotNull @PositiveOrZero BigDecimal retailPrice,
        @NotNull @PositiveOrZero BigDecimal wholesalePrice,
        @PositiveOrZero int minQuantity,
        boolean active,
        @NotNull Long unitId
) {}