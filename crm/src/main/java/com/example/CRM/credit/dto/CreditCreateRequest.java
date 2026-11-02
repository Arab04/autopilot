package com.example.CRM.credit.dto;

import jakarta.validation.constraints.NotNull;

import java.time.LocalDate;

public record CreditCreateRequest(
        @NotNull Long saleId,
        @NotNull String customerName,
        @NotNull String phone,
        @NotNull LocalDate dueDate
) {}
