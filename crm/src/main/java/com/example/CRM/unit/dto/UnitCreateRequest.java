package com.example.CRM.unit.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;

public record UnitCreateRequest(
        @NotBlank String name,
        @NotBlank String symbol,
        @NotBlank String category,
        boolean mainUnit,
        @Positive double coefficient
) {}