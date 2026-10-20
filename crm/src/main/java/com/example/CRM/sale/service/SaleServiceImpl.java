package com.example.CRM.sale.service;

import com.example.CRM.product.entity.ProductEntity;
import com.example.CRM.product.repository.ProductRepository;
import com.example.CRM.sale.dto.CheckoutRequest;
import com.example.CRM.sale.entity.SaleEntity;
import com.example.CRM.sale.entity.SaleItemEntity;
import com.example.CRM.sale.repository.SaleRepository;
import com.example.CRM.settings.service.SettingsService;
import com.example.CRM.stock.entity.StockEntity;
import com.example.CRM.stock.repository.StockRepository;
import jakarta.persistence.EntityNotFoundException;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class SaleServiceImpl implements SaleService {

    private final SaleRepository saleRepo;
    private final ProductRepository productRepo;
    private final StockRepository stockRepo;
    private final SettingsService settingsService;

    @Override
    @Transactional
    public SaleEntity checkout(CheckoutRequest req) {

        double taxPercent = settingsService.getSettings().taxPercent();

        SaleEntity sale = new SaleEntity();
        sale.setWarehouseId(req.warehouseId());
        sale.setCustomerName(req.customerName());
        sale.setCustomerPhone(req.customerPhone());
        sale.setPaymentType(req.paymentType());
        sale.setCreatedAt(LocalDateTime.now());

        BigDecimal subtotal = BigDecimal.ZERO;

        for (CheckoutRequest.CheckoutItem item : req.items()) {
            ProductEntity product = productRepo.findById(item.productId())
                    .orElseThrow(() -> new EntityNotFoundException("Product not found: " + item.productId()));

            // stock check + decrement
            StockEntity stock = stockRepo.findByProduct_IdAndWarehouse_Id(product.getId(), req.warehouseId())
                    .orElseThrow(() -> new IllegalArgumentException("Stock not found for product " + product.getId()));

            if (stock.getQuantity() < item.quantity()) {
                throw new IllegalArgumentException("Not enough stock for product " + product.getName());
            }
            stock.setQuantity(stock.getQuantity() - item.quantity());
            stockRepo.save(stock);

            BigDecimal price = product.getRetailPrice(); // POS -> chakana
            BigDecimal lineTotal = price.multiply(BigDecimal.valueOf(item.quantity()));

            SaleItemEntity si = SaleItemEntity.builder()
                    .sale(sale)
                    .product(product)
                    .quantity(item.quantity())
                    .price(price)
                    .lineTotal(lineTotal)
                    .build();

            sale.getItems().add(si);
            subtotal = subtotal.add(lineTotal);
        }

        BigDecimal taxAmount = subtotal.multiply(BigDecimal.valueOf(taxPercent)).divide(BigDecimal.valueOf(100));
        BigDecimal total = subtotal.add(taxAmount);

        sale.setSubtotal(subtotal);
        sale.setTaxAmount(taxAmount);
        sale.setTotal(total);

        if ("CASH".equalsIgnoreCase(req.paymentType())) {
            sale.setStatus("PAID");
        } else {
            sale.setStatus("OPEN");
        }

        return saleRepo.save(sale);
    }

    @Override
    public List<SaleEntity> list() {
        return saleRepo.findAll();
    }
}