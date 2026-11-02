package com.example.CRM.credit.dto;


import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

public record CreditPayRequest(@NotNull BigDecimal amount) {}
