package com.example.CRM.credit.service;


import com.example.CRM.credit.dto.CreditCreateRequest;
import com.example.CRM.credit.dto.CreditPayRequest;
import com.example.CRM.credit.entity.CreditEntity;

import java.util.List;

public interface CreditService {
    CreditEntity create(CreditCreateRequest req);
    CreditEntity pay(Long id, CreditPayRequest req);
    List<CreditEntity> list();
}