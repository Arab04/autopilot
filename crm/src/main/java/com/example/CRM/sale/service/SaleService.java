package com.example.CRM.sale.service;

import com.example.CRM.sale.dto.CheckoutRequest;
import com.example.CRM.sale.entity.SaleEntity;

import java.util.List;

public interface SaleService {
    SaleEntity checkout(CheckoutRequest req);
    List<SaleEntity> list();
}
