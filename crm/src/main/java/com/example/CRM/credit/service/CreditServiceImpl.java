package com.example.CRM.credit.service;

import com.example.CRM.credit.dto.CreditCreateRequest;
import com.example.CRM.credit.dto.CreditPayRequest;
import com.example.CRM.credit.entity.CreditEntity;
import com.example.CRM.credit.repository.CreditRepository;
import com.example.CRM.sale.entity.SaleEntity;
import com.example.CRM.sale.repository.SaleRepository;
import jakarta.persistence.EntityNotFoundException;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

@Service
@RequiredArgsConstructor
public class CreditServiceImpl implements CreditService {

    private final CreditRepository creditRepo;
    private final SaleRepository saleRepo;

    @Override
    @Transactional
    public CreditEntity create(CreditCreateRequest req) {
        SaleEntity sale = saleRepo.findById(req.saleId())
                .orElseThrow(() -> new EntityNotFoundException("Sale not found"));

        CreditEntity credit = CreditEntity.builder()
                .saleId(sale.getId())
                .customerName(req.customerName())
                .phone(req.phone())
                .totalAmount(sale.getTotal())
                .paidAmount(BigDecimal.ZERO)
                .dueDate(req.dueDate())
                .status("OPEN")
                .build();

        return creditRepo.save(credit);
    }

    @Override
    @Transactional
    public CreditEntity pay(Long id, CreditPayRequest req) {
        CreditEntity c = creditRepo.findById(id).orElseThrow(() -> new EntityNotFoundException("Credit not found"));
        c.setPaidAmount(c.getPaidAmount().add(req.amount()));

        if (c.getPaidAmount().compareTo(c.getTotalAmount()) >= 0) {
            c.setStatus("CLOSED");
        }
        return creditRepo.save(c);
    }

    @Override
    public List<CreditEntity> list() {
        return creditRepo.findAll();
    }
}
